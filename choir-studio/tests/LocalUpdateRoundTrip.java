package cn.hesheng.choirstudio;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;

public class LocalUpdateRoundTrip {
    public static void main(String[] args)throws Exception{
        File fixture=new File(args[0]);
        byte[] payload=Files.readAllBytes(new File(fixture,"payload").toPath());
        UpdateFiles.verifiedPayload(payload,Files.readAllBytes(new File(fixture,"signature").toPath()),Files.readAllBytes(new File(fixture,"key.der").toPath()));
        List<UpdateFiles.Entry> entries=new ArrayList<>();
        for(String line:Files.readAllLines(new File(fixture,"files.tsv").toPath(),StandardCharsets.UTF_8)){
            String[] fields=line.split("\t");entries.add(new UpdateFiles.Entry(fields[0],Long.parseLong(fields[1]),fields[2]));
        }
        URL base=new URL(new String(Files.readAllBytes(new File(fixture,"server.txt").toPath()),StandardCharsets.UTF_8));
        File root=new File(fixture,"phone-storage");
        try{
            File downloaded=UpdateFiles.stage(root,entries,null,e->{
                HttpURLConnection c=(HttpURLConnection)new URL(base,"local-update/files/"+e.hash).openConnection();
                c.setConnectTimeout(6000);c.setReadTimeout(15000);
                if(c.getResponseCode()!=200)throw new IOException("HTTP download failed");
                return new FilterInputStream(c.getInputStream()){@Override public void close()throws IOException{super.close();c.disconnect();}};
            },(done,total)->{});
            // Read the installed files again with the network source deliberately unavailable.
            File offline=UpdateFiles.stage(root,entries,e->new FileInputStream(new File(downloaded,e.path)),e->{throw new IOException("offline");},(done,total)->{});
            if(!new File(offline,"songs/chi-le-ge/performance.mid").isFile())throw new AssertionError();
            System.out.println("Node signed manifest -> Java verifier -> HTTP download -> offline reuse: "+entries.size()+" files passed.");
        }finally{if(root.exists())UpdateFiles.delete(root);}
    }
}
