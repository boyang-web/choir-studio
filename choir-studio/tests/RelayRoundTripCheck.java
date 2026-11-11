package cn.hesheng.choirstudio;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;

public class RelayRoundTripCheck {
    private static int checks=0;
    private static void check(boolean value){if(!value)throw new AssertionError();checks++;}
    private static HttpURLConnection connection(URL base,String path)throws Exception{
        HttpURLConnection c=(HttpURLConnection)new URL(base,path).openConnection();c.setConnectTimeout(3000);c.setReadTimeout(5000);return c;
    }
    private static Map<String,RelayHttpServer.Resource> resources(File root,List<UpdateFiles.Entry> entries){
        Map<String,RelayHttpServer.Resource> result=new HashMap<>();
        for(UpdateFiles.Entry e:entries)result.put(e.hash,new RelayHttpServer.Resource(e.size,()->new FileInputStream(new File(root,e.path))));
        return result;
    }
    private static void verifyEnvelope(byte[] bytes,File fixture)throws Exception{
        check(Arrays.equals(bytes,Files.readAllBytes(new File(fixture,"envelope.json").toPath())));
        UpdateFiles.verifiedPayload(Files.readAllBytes(new File(fixture,"payload").toPath()),Files.readAllBytes(new File(fixture,"signature").toPath()),Files.readAllBytes(new File(fixture,"key.der").toPath()));checks++;
    }
    public static void main(String[] args)throws Exception{
        File fixture=new File(args[0]),publicRoot=new File(args[1]);
        byte[] envelope=Files.readAllBytes(new File(fixture,"envelope.json").toPath());
        List<UpdateFiles.Entry> entries=new ArrayList<>();
        for(String line:Files.readAllLines(new File(fixture,"files.tsv").toPath(),StandardCharsets.UTF_8)){
            String[] f=line.split("\t");entries.add(new UpdateFiles.Entry(f[0],Long.parseLong(f[1]),f[2]));
        }
        File phones=Files.createTempDirectory("choir-relay-").toFile();
        byte[] fakeApk="apk-binary".getBytes(StandardCharsets.UTF_8);
        RelayHttpServer.Resource apk=new RelayHttpServer.Resource(fakeApk.length,()->new ByteArrayInputStream(fakeApk));
        try(RelayHttpServer sender=new RelayHttpServer(0,envelope,resources(publicRoot,entries),apk,"offline instructions",true)){
            URL base=new URL("http://127.0.0.1:"+sender.port()+"/");
            verifyEnvelope(UpdateFiles.readLimited(connection(base,"local-update/manifest").getInputStream(),6*1024*1024),fixture);
            File phoneB=UpdateFiles.stage(phones,entries,null,e->connection(base,"local-update/files/"+e.hash).getInputStream(),(done,total)->{});
            check(new File(phoneB,"songs/chi-le-ge/performance.mid").isFile());
            for(String bad:Arrays.asList("private.pem","../.update-keys/private.pem","local-update/files/../index.html","local-update/files/0000")){
                HttpURLConnection c=connection(base,bad);check(c.getResponseCode()==404);c.disconnect();
            }
            HttpURLConnection post=connection(base,"local-update/manifest");post.setRequestMethod("POST");check(post.getResponseCode()==405);post.disconnect();
            HttpURLConnection head=connection(base,"local-update/manifest");head.setRequestMethod("HEAD");check(head.getResponseCode()==200&&head.getContentLengthLong()==envelope.length);head.disconnect();
            check(Arrays.equals(fakeApk,UpdateFiles.readLimited(connection(base,"download/choir-studio.apk").getInputStream(),1000)));
            // A second phone serves the received files and original signature to a third phone.
            try(RelayHttpServer next=new RelayHttpServer(0,envelope,resources(phoneB,entries),apk,"next hop",true)){
                URL other=new URL("http://127.0.0.1:"+next.port()+"/");
                verifyEnvelope(UpdateFiles.readLimited(connection(other,"local-update/manifest").getInputStream(),6*1024*1024),fixture);
                File phoneC=UpdateFiles.stage(phones,entries,null,e->connection(other,"local-update/files/"+e.hash).getInputStream(),(done,total)->{});
                for(UpdateFiles.Entry e:entries)check(Arrays.equals(Files.readAllBytes(new File(phoneC,e.path).toPath()),Files.readAllBytes(new File(publicRoot,e.path).toPath())));
            }
        }finally{UpdateFiles.delete(phones);}
        System.out.println("Offline phone A -> B -> C relay: "+entries.size()+" files, "+checks+" checks passed; original signature preserved.");
    }
}
