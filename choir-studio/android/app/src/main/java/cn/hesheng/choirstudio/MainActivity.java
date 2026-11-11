package cn.hesheng.choirstudio;

import com.getcapacitor.BridgeActivity;
import android.os.Bundle;
import android.view.WindowManager;
import android.content.SharedPreferences;
import android.os.Handler;
import android.os.Looper;
import java.io.File;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        SharedPreferences prefs=getSharedPreferences("LocalUpdates",0);
        long binaryVersion=0;
        try{binaryVersion=getPackageManager().getPackageInfo(getPackageName(),0).versionCode;}catch(Exception ignored){}
        if(prefs.getLong("binaryVersion",-1)!=binaryVersion){
            prefs.edit().putLong("binaryVersion",binaryVersion).remove("active").remove("previous").putBoolean("pending",false).commit();
        }else if(prefs.getBoolean("pending",false)){
            // A process exit before the new page reported ready restores the previous version.
            prefs.edit().putString("active",prefs.getString("previous","")).putBoolean("pending",false).commit();
        }
        registerPlugin(LocalUpdatesPlugin.class);
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        String active=prefs.getString("active","");
        if(!active.isEmpty() && new File(active,"index.html").isFile() && bridge!=null)bridge.setServerBasePath(active);
        else prefs.edit().remove("active").apply();
    }

    public void watchUpdate(){
        final SharedPreferences prefs=getSharedPreferences("LocalUpdates",0);
        final String candidate=prefs.getString("active","");
        new Handler(Looper.getMainLooper()).postDelayed(()->{
            if(!isFinishing() && bridge!=null && prefs.getBoolean("pending",false) && candidate.equals(prefs.getString("active",""))){
                String previous=prefs.getString("previous","");
                prefs.edit().putString("active",previous).putBoolean("pending",false).commit();
                if(previous.isEmpty())bridge.setServerAssetPath("public");else bridge.setServerBasePath(previous);
            }
        },30000);
    }
}
