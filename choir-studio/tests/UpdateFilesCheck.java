package cn.hesheng.choirstudio;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.*;
import java.util.*;

/** Executes the same verifier and staging implementation compiled into Android. */
public class UpdateFilesCheck {
    private interface Action {void run() throws Exception;}
    private static int checks=0;
    private static void check(boolean yes){if(!yes)throw new AssertionError();checks++;}
    private static void fails(Action action)throws Exception {try{action.run();}catch(Exception expected){checks++;return;}throw new AssertionError("Expected rejection");}
    public static void main(String[] args)throws Exception {
        for(String address:Arrays.asList("http://192.168.1.2:5173","http://10.0.0.2:5173/","http://172.16.0.1:5173"))check(UpdateFiles.localAddress(address)!=null);
        for(String address:Arrays.asList("https://192.168.1.2","http://example.com","http://127.0.0.1","http://8.8.8.8","http://192.168.999.1","http://192.168.1.2/a","http://user@192.168.1.2","http://192.168.1.2?x=1"))fails(()->UpdateFiles.localAddress(address));
        KeyPairGenerator generator=KeyPairGenerator.getInstance("RSA");generator.initialize(2048);KeyPair pair=generator.generateKeyPair();
        byte[] payload="signed manifest".getBytes(StandardCharsets.UTF_8);
        Signature signer=Signature.getInstance("SHA256withRSA");signer.initSign(pair.getPrivate());signer.update(payload);byte[] sig=signer.sign();
        check(Arrays.equals(payload,UpdateFiles.verifiedPayload(payload,sig,pair.getPublic().getEncoded())));
        fails(()->UpdateFiles.verifiedPayload("tampered".getBytes(StandardCharsets.UTF_8),sig,pair.getPublic().getEncoded()));
        fails(()->UpdateFiles.verifiedPayload(payload,sig,generator.generateKeyPair().getPublic().getEncoded()));
        Map<String,byte[]> contents=new LinkedHashMap<>();
        for(String name:Arrays.asList("index.html","app.js","local-updates.js","songs/catalog.json","vendor/tone.js","vendor/midi.js"))contents.put(name,("new-"+name).getBytes(StandardCharsets.UTF_8));
        List<UpdateFiles.Entry> entries=new ArrayList<>();
        for(Map.Entry<String,byte[]> e:contents.entrySet())entries.add(new UpdateFiles.Entry(e.getKey(),e.getValue().length,UpdateFiles.digest(e.getValue())));
        UpdateFiles.validate(entries);
        List<UpdateFiles.Entry> bad=new ArrayList<>(entries);bad.add(new UpdateFiles.Entry("../escape",0,UpdateFiles.digest(new byte[0])));fails(()->UpdateFiles.validate(bad));
        List<UpdateFiles.Entry> duplicate=new ArrayList<>(entries);duplicate.add(entries.get(0));fails(()->UpdateFiles.validate(duplicate));
        fails(()->UpdateFiles.validate(Collections.emptyList()));
        File root=Files.createTempDirectory("choir-native-update-").toFile();
        try{
            File active=new File(root,"old");check(active.mkdir());Files.write(new File(active,"index.html").toPath(),"old version".getBytes(StandardCharsets.UTF_8));
            File staged=UpdateFiles.stage(root,entries,f->new ByteArrayInputStream(contents.get(f.path)),f->{throw new IOException("network should not be needed");},(done,total)->{});
            for(UpdateFiles.Entry e:entries)check(Arrays.equals(Files.readAllBytes(new File(staged,e.path).toPath()),contents.get(e.path)));
            check(new String(Files.readAllBytes(new File(active,"index.html").toPath()),StandardCharsets.UTF_8).equals("old version"));
            int count=root.list().length;
            fails(()->UpdateFiles.stage(root,entries,null,f->{if(f.path.equals("app.js"))throw new IOException("connection lost");return new ByteArrayInputStream(contents.get(f.path));},(done,total)->{}));
            check(root.list().length==count);
            fails(()->UpdateFiles.stage(root,entries,null,f->new ByteArrayInputStream(new byte[]{1}),(done,total)->{}));check(root.list().length==count);
            fails(()->UpdateFiles.stage(root,entries,null,f->new ByteArrayInputStream(new byte[4096]),(done,total)->{}));check(root.list().length==count);
            int[] downloads={0};
            File repaired=UpdateFiles.stage(root,entries,f->new ByteArrayInputStream(new byte[]{0}),f->{downloads[0]++;return new ByteArrayInputStream(contents.get(f.path));},(done,total)->{});
            check(downloads[0]==entries.size());check(new File(repaired,"index.html").isFile());
            System.out.println("Native update verifier/staging: "+checks+" checks passed.");
        }finally{UpdateFiles.delete(root);}
    }
}
