package cn.hesheng.choirstudio;

import android.app.*;
import android.content.*;
import android.os.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class UpdateShareService extends Service {
    private static volatile boolean running=false;
    public static volatile String lastError="";
    private RelayHttpServer server;
    private PowerManager.WakeLock wake;
    private final Handler handler=new Handler(Looper.getMainLooper());
    public static boolean isRunning(){return running;}
    public static synchronized void start(Context context){
        if(running)return;lastError="";running=true;
        try{
            Intent intent=new Intent(context,UpdateShareService.class);
            if(Build.VERSION.SDK_INT>=26)context.startForegroundService(intent);else context.startService(intent);
        }catch(Exception error){running=false;throw error;}
    }
    public static List<String> addresses(){
        List<String> addresses=new ArrayList<>();
        if(!running)return addresses;
        try{
            Enumeration<NetworkInterface> interfaces=NetworkInterface.getNetworkInterfaces();
            while(interfaces.hasMoreElements()){
                NetworkInterface face=interfaces.nextElement();if(!face.isUp()||face.isLoopback())continue;
                Enumeration<InetAddress> ips=face.getInetAddresses();
                while(ips.hasMoreElements()){
                    InetAddress ip=ips.nextElement();
                    if(ip instanceof Inet4Address && ip.isSiteLocalAddress()){
                        String name=face.getName().toLowerCase(Locale.ROOT);
                        if(name.contains("rmnet")||name.contains("ccmni")||name.contains("pdp")||name.contains("tun"))continue;
                        addresses.add("http://"+ip.getHostAddress()+":5174");
                    }
                }
            }
        }catch(Exception ignored){}
        return addresses;
    }
    @Override public IBinder onBind(Intent intent){return null;}
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        if(intent!=null&&"stop".equals(intent.getAction())){stopSelf();return START_NOT_STICKY;}
        if(server!=null)return START_NOT_STICKY;
        running=true;
        try{
            NotificationManager manager=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
            if(Build.VERSION.SDK_INT>=26)manager.createNotificationChannel(new NotificationChannel("offline-share","离线分享",NotificationManager.IMPORTANCE_LOW));
            Intent stop=new Intent(this,UpdateShareService.class).setAction("stop");
            PendingIntent action=PendingIntent.getService(this,0,stop,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
            Intent open=new Intent(this,MainActivity.class);
            PendingIntent openApp=PendingIntent.getActivity(this,1,open,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
            Notification.Builder notice=Build.VERSION.SDK_INT>=26?new Notification.Builder(this,"offline-share"):new Notification.Builder(this);
            notice.setSmallIcon(android.R.drawable.stat_sys_upload).setContentTitle("和声练习室 · 正在离线分享").setContentText("连接本机热点后可接收更新；30 分钟后自动停止")
                .setContentIntent(openApp).setOngoing(true).addAction(android.R.drawable.ic_delete,"停止分享",action);
            startForeground(1701,notice.build());
            wake=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"ChoirStudio:OfflineShare");
            wake.acquire(30*60*1000L);
            handler.postDelayed(this::stopSelf,30*60*1000L);
            String active=getSharedPreferences("LocalUpdates",0).getString("active","");
            byte[] envelope=UpdateFiles.readLimited(active.isEmpty()?getAssets().open("update-builtin-envelope.json"):new FileInputStream(new File(active,".update-envelope.json")),6*1024*1024);
            JSONObject outer=new JSONObject(new String(envelope,StandardCharsets.UTF_8));
            byte[] payload=android.util.Base64.decode(outer.getString("payload"),android.util.Base64.DEFAULT);
            JSONObject manifest=new JSONObject(new String(payload,StandardCharsets.UTF_8));
            JSONArray array=manifest.getJSONArray("files");Map<String,RelayHttpServer.Resource> files=new HashMap<>();
            List<UpdateFiles.Entry> entries=new ArrayList<>();
            for(int i=0;i<array.length();i++){
                JSONObject f=array.getJSONObject(i);String path=f.getString("path"),hash=f.getString("sha256");long size=f.getLong("size");
                entries.add(new UpdateFiles.Entry(path,size,hash));
                files.put(hash,new RelayHttpServer.Resource(size,()->active.isEmpty()?getAssets().open("public/"+path):new FileInputStream(new File(active,path))));
            }
            UpdateFiles.validate(entries);
            File apk=new File(getPackageCodePath());
            String landing="<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>和声练习室 · 离线分享</title><style>body{font:17px system-ui;line-height:1.8;max-width:580px;margin:40px auto;padding:20px;background:#10151e;color:#edf4ff}a{color:#b6d8ff}</style><h1>和声练习室 · 离线分享</h1><p>已安装应用：连接分享者的热点，打开应用的「控制台 → 局域网更新」，填写当前浏览器地址，再检查并下载更新。</p><p>尚未安装：<a href='/download/choir-studio.apk'>下载安卓安装包</a>，安装后按上面步骤接收分享者的当前内容。</p><p>完成保存后可以断开热点，继续离线练习。</p>";
            server=new RelayHttpServer(5174,envelope,files,new RelayHttpServer.Resource(apk.length(),()->new FileInputStream(apk)),landing,false);
        }catch(Exception error){lastError="无法开启分享："+(error.getMessage()==null?"请重试":error.getMessage());stopSelf();}
        return START_NOT_STICKY;
    }
    @Override public void onTimeout(int startId,int type){stopSelf();}
    @Override public void onDestroy(){
        running=false;handler.removeCallbacksAndMessages(null);
        if(server!=null)try{server.close();}catch(IOException ignored){}
        if(wake!=null&&wake.isHeld())wake.release();
        stopForeground(true);super.onDestroy();
    }
}
