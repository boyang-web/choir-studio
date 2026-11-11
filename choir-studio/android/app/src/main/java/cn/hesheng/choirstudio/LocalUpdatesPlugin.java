package cn.hesheng.choirstudio;

import android.content.SharedPreferences;
import android.util.Base64;
import com.getcapacitor.*;
import com.getcapacitor.annotation.CapacitorPlugin;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.atomic.AtomicBoolean;

@CapacitorPlugin(name="LocalUpdates")
public class LocalUpdatesPlugin extends Plugin {
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private final AtomicBoolean busy=new AtomicBoolean(false);
    private volatile int completed=0,total=0;
    private JSONObject prepared;
    private String preparedEnvelope;
    private URL source;
    private String ticket;
    private SharedPreferences prefs(){return getContext().getSharedPreferences("LocalUpdates",0);}
    private File root(){return new File(getContext().getFilesDir(),"local-updates");}
    private String text(InputStream in,int limit) throws IOException {return new String(UpdateFiles.readLimited(in,limit),StandardCharsets.UTF_8);}
    private JSONObject current() throws Exception {
        String active=prefs().getString("active","");
        return new JSONObject(active.isEmpty()?text(getContext().getAssets().open("update-builtin.json"),8192):text(new FileInputStream(new File(active,".update-info.json")),8192));
    }
    private InputStream request(URL base,String path) throws Exception {
        HttpURLConnection connection=(HttpURLConnection)new URL(base,path).openConnection();
        connection.setConnectTimeout(6000);connection.setReadTimeout(15000);connection.setInstanceFollowRedirects(false);
        connection.setRequestProperty("Cache-Control","no-cache");
        try{
            if(connection.getResponseCode()!=200)throw new IOException("电脑未提供此更新，请重新检查更新");
            return new FilterInputStream(connection.getInputStream()){
                @Override public void close() throws IOException {try{super.close();}finally{connection.disconnect();}}
            };
        }catch(Exception error){connection.disconnect();throw error;}
    }
    private List<UpdateFiles.Entry> entries(JSONObject manifest) throws Exception {
        JSONArray array=manifest.getJSONArray("files");List<UpdateFiles.Entry> result=new ArrayList<>();
        for(int i=0;i<array.length();i++){
            JSONObject f=array.getJSONObject(i);result.add(new UpdateFiles.Entry(f.getString("path"),f.getLong("size"),f.getString("sha256")));
        }
        UpdateFiles.validate(result);return result;
    }
    private void reject(PluginCall call,Exception error){
        String message=error instanceof SocketTimeoutException?"连接超时，请确认电脑已启动练习室，且手机与电脑连接同一 Wi-Fi":
            error instanceof ConnectException||error instanceof NoRouteToHostException?"连接不到电脑，请检查 Wi-Fi、电脑地址和防火墙":error.getMessage();
        call.reject(message==null?"更新失败，原有内容仍可使用":message);
    }
    @PluginMethod public void status(PluginCall call){
        try{
            JSONObject info=current();JSObject result=new JSObject();
            result.put("version",info.getString("version"));result.put("revision",info.getString("revision"));
            result.put("source",prefs().getString("source",""));result.put("downloaded",!prefs().getString("active","").isEmpty());
            result.put("completed",completed);result.put("total",total);result.put("busy",busy.get());
            result.put("canShare",true);result.put("sharing",UpdateShareService.isRunning());
            result.put("shareAddresses",new JSArray(UpdateShareService.addresses()));
            result.put("shareError",UpdateShareService.lastError);
            call.resolve(result);
        }catch(Exception error){reject(call,error);}
    }
    @PluginMethod public void check(PluginCall call){
        if(!busy.compareAndSet(false,true)){call.reject("正在处理更新，请稍候");return;}
        worker.execute(()->{
            try{
                prepared=null;ticket=null;
                URL address=UpdateFiles.localAddress(call.getString("source",""));
                JSONObject envelope=new JSONObject(text(request(address,"local-update/manifest"),6*1024*1024));
                byte[] payload=Base64.decode(envelope.getString("payload"),Base64.DEFAULT);
                byte[] signature=Base64.decode(envelope.getString("signature"),Base64.DEFAULT);
                String pem=text(getContext().getAssets().open("update-public-key.pem"),16384);
                byte[] der=Base64.decode(pem.replace("-----BEGIN PUBLIC KEY-----","").replace("-----END PUBLIC KEY-----",""),Base64.DEFAULT);
                UpdateFiles.verifiedPayload(payload,signature,der);
                JSONObject manifest=new JSONObject(new String(payload,StandardCharsets.UTF_8));
                if(manifest.getInt("protocol")!=1 || manifest.getInt("minNative")>1)throw new IOException("此更新需要安装新版 APK");
                List<UpdateFiles.Entry> files=entries(manifest);
                String revision=manifest.getString("revision");
                if(!revision.matches("[a-f0-9]{64}"))throw new IOException("更新版本标识无效");
                boolean available=!revision.equals(current().getString("revision"));
                source=address;prepared=manifest;preparedEnvelope=envelope.toString();ticket=UUID.randomUUID().toString();
                prefs().edit().putString("source",address.toString()).apply();
                long size=0;for(UpdateFiles.Entry f:files)size+=f.size;
                JSObject result=new JSObject();result.put("available",available);result.put("ticket",ticket);
                result.put("version",manifest.getString("version"));result.put("revision",revision);result.put("bytes",size);
                call.resolve(result);
            }catch(Exception error){reject(call,error);}finally{busy.set(false);}
        });
    }
    @PluginMethod public void install(PluginCall call){
        if(UpdateShareService.isRunning()){call.reject("请先停止分享，再更新此手机的内容");return;}
        if(!busy.compareAndSet(false,true)){call.reject("正在处理更新，请稍候");return;}
        worker.execute(()->{
            File stage=null;
            try{
                if(prepared==null || !Objects.equals(ticket,call.getString("ticket")))throw new IOException("请先检查更新");
                List<UpdateFiles.Entry> files=entries(prepared);completed=0;total=files.size();
                String active=prefs().getString("active","");URL address=source;
                long deadline=System.currentTimeMillis()+10*60*1000;
                stage=UpdateFiles.stage(root(),files,
                    f->active.isEmpty()?getContext().getAssets().open("public/"+f.path):new FileInputStream(new File(active,f.path)),
                    f->{if(System.currentTimeMillis()>deadline)throw new IOException("更新耗时过长，请重新检查更新");return request(address,"local-update/files/"+f.hash);},
                    (count,all)->{completed=count;total=all;});
                JSONObject info=new JSONObject();info.put("version",prepared.getString("version"));info.put("revision",prepared.getString("revision"));
                try(FileOutputStream out=new FileOutputStream(new File(stage,".update-info.json"))){out.write(info.toString().getBytes(StandardCharsets.UTF_8));out.getFD().sync();}
                try(FileOutputStream out=new FileOutputStream(new File(stage,".update-envelope.json"))){out.write(preparedEnvelope.getBytes(StandardCharsets.UTF_8));out.getFD().sync();}
                final String path=stage.getAbsolutePath();
                if(!prefs().edit().putString("previous",active).putString("active",path).putBoolean("pending",true).commit())throw new IOException("无法保存更新状态");
                ticket=null;prepared=null;call.resolve();
                getActivity().runOnUiThread(()->{
                    getBridge().setServerBasePath(path);
                    ((MainActivity)getActivity()).watchUpdate();
                });
            }catch(Exception error){
                if(stage!=null)try{UpdateFiles.delete(stage);}catch(Exception ignored){}
                reject(call,error);
            }finally{busy.set(false);}
        });
    }
    @PluginMethod public void ready(PluginCall call){
        prefs().edit().putBoolean("pending",false).apply();call.resolve();
        // Keep the active and previous complete versions; remove abandoned downloads.
        worker.execute(()->{
            String active=prefs().getString("active",""),previous=prefs().getString("previous","");
            File[] dirs=root().listFiles();if(dirs!=null)for(File dir:dirs){
                if(!dir.getAbsolutePath().equals(active)&&!dir.getAbsolutePath().equals(previous))try{UpdateFiles.delete(dir);}catch(Exception ignored){}
            }
        });
    }
    @PluginMethod public void restore(PluginCall call){
        if(UpdateShareService.isRunning()){call.reject("请先停止分享，再恢复安装版内容");return;}
        if(!busy.compareAndSet(false,true)){call.reject("正在处理更新，请稍候");return;}
        try{
            if(!prefs().edit().remove("active").remove("previous").putBoolean("pending",false).commit())throw new IOException("恢复失败，请重试");
            call.resolve();getActivity().runOnUiThread(()->getBridge().setServerAssetPath("public"));
        }catch(Exception error){reject(call,error);}finally{busy.set(false);}
    }
    @PluginMethod public void startShare(PluginCall call){
        if(!busy.compareAndSet(false,true)){call.reject("正在处理更新，请稍候");return;}
        try{UpdateShareService.start(getContext());call.resolve();}
        catch(Exception error){reject(call,error);}finally{busy.set(false);}
    }
    @PluginMethod public void stopShare(PluginCall call){
        getContext().stopService(new android.content.Intent(getContext(),UpdateShareService.class));call.resolve();
    }
}
