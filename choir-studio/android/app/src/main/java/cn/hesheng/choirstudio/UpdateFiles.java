package cn.hesheng.choirstudio;

import java.io.*;
import java.net.*;
import java.security.*;
import java.security.spec.X509EncodedKeySpec;
import java.util.*;

/** Platform independent update verification and staging. Never mutates the active version. */
public final class UpdateFiles {
    public static final long MAX_TOTAL = 300L * 1024 * 1024;
    public static final class Entry {
        public final String path, hash;
        public final long size;
        public Entry(String path, long size, String hash) { this.path=path; this.size=size; this.hash=hash; }
    }
    public interface Source { InputStream open(Entry file) throws Exception; }
    public interface Progress { void done(int count, int total); }

    public static URL localAddress(String value) throws Exception {
        URL url=new URL(value.trim());
        if (!url.getProtocol().equals("http") || url.getUserInfo()!=null || url.getQuery()!=null || url.getRef()!=null
            || !(url.getPath().isEmpty() || url.getPath().equals("/")))
            throw new IOException("请填写电脑的 http://局域网IP:端口 地址");
        // Literal IPv4 only: no DNS rebinding, internet hosts, redirects or credentials.
        String host=url.getHost();
        if (!host.matches("[0-9]{1,3}(\\.[0-9]{1,3}){3}")) throw new IOException("请使用电脑的局域网 IPv4 地址");
        String[] pieces=host.split("\\."); int[] ip=new int[4];
        for(int i=0;i<4;i++){ip[i]=Integer.parseInt(pieces[i]);if(ip[i]>255)throw new IOException("IP 地址无效");}
        if (!(ip[0]==10 || (ip[0]==172 && ip[1]>=16 && ip[1]<=31) || (ip[0]==192 && ip[1]==168)))
            throw new IOException("更新源必须是同一局域网内的电脑");
        if(url.getPort()==0 || url.getPort()>65535)throw new IOException("端口无效");
        return new URL("http",host,url.getPort(),"/");
    }

    public static byte[] verifiedPayload(byte[] payload, byte[] signature, byte[] publicDer) throws Exception {
        PublicKey key=KeyFactory.getInstance("RSA").generatePublic(new X509EncodedKeySpec(publicDer));
        Signature verifier=Signature.getInstance("SHA256withRSA"); verifier.initVerify(key); verifier.update(payload);
        if(!verifier.verify(signature))throw new IOException("更新签名不匹配，请使用最初提供此安装包的电脑");
        return payload;
    }

    public static String digest(byte[] data) throws Exception {return hex(MessageDigest.getInstance("SHA-256").digest(data));}
    private static String hex(byte[] bytes){StringBuilder b=new StringBuilder();for(byte v:bytes)b.append(String.format(Locale.ROOT,"%02x",v&255));return b.toString();}
    public static void validate(List<Entry> files) throws IOException {
        Set<String> paths=new HashSet<>();long total=0;
        if(files.size()>4096)throw new IOException("更新文件过多");
        for(Entry f:files){
            if(!f.path.matches("[A-Za-z0-9_./-]+") || f.path.startsWith("/") || f.path.contains("//"))throw new IOException("更新路径无效");
            for(String segment:f.path.split("/"))if(segment.isEmpty() || segment.equals(".") || segment.equals(".."))throw new IOException("更新路径无效");
            if(!paths.add(f.path) || f.size<0 || f.size>100L*1024*1024 || !f.hash.matches("[a-f0-9]{64}"))throw new IOException("更新清单无效");
            total+=f.size;
        }
        if(total>MAX_TOTAL || !paths.containsAll(Arrays.asList("index.html","app.js","local-updates.js","songs/catalog.json","vendor/tone.js","vendor/midi.js")))
            throw new IOException("更新不完整或过大");
    }

    private static void copyVerified(InputStream input, File dest, Entry entry) throws Exception {
        MessageDigest digest=MessageDigest.getInstance("SHA-256");long count=0;
        try(InputStream in=input;OutputStream out=new FileOutputStream(dest)){
            byte[] bytes=new byte[65536];int n;
            while((n=in.read(bytes))!=-1){count+=n;if(count>entry.size)throw new IOException("更新文件大小不符");digest.update(bytes,0,n);out.write(bytes,0,n);}
        }
        if(count!=entry.size || !hex(digest.digest()).equals(entry.hash))throw new IOException("更新文件校验失败，请重新检查更新");
    }

    public static File stage(File root, List<Entry> files, Source cached, Source remote, Progress progress) throws Exception {
        validate(files);
        if(!root.exists() && !root.mkdirs())throw new IOException("无法建立更新目录");
        long total=0;for(Entry e:files)total+=e.size;
        if(root.getUsableSpace()<total+20L*1024*1024)throw new IOException("手机存储空间不足");
        File stage=new File(root,"version-"+UUID.randomUUID());
        if(!stage.mkdir())throw new IOException("无法保存更新");
        try{
            int count=0;
            for(Entry e:files){
                File dest=new File(stage,e.path);
                if(!dest.getCanonicalPath().startsWith(stage.getCanonicalPath()+File.separator))throw new IOException("更新路径越界");
                if(!dest.getParentFile().isDirectory()&&!dest.getParentFile().mkdirs())throw new IOException("无法保存更新文件");
                boolean reused=false;
                if(cached!=null){try{copyVerified(cached.open(e),dest,e);reused=true;}catch(Exception ignored){}}
                if(!reused)copyVerified(remote.open(e),dest,e);
                progress.done(++count,files.size());
            }
            return stage;
        }catch(Exception error){delete(stage);throw error;}
    }
    public static void delete(File file) throws IOException {
        if(file.isDirectory()){File[] children=file.listFiles();if(children!=null)for(File child:children)delete(child);}
        if(file.exists()&&!file.delete())throw new IOException("无法清理未完成的更新");
    }
    public static byte[] readLimited(InputStream input,int limit) throws IOException {
        try(InputStream in=input;ByteArrayOutputStream out=new ByteArrayOutputStream()){
            byte[] bytes=new byte[8192];int n;
            while((n=in.read(bytes))!=-1){if(out.size()+n>limit)throw new IOException("更新清单过大");out.write(bytes,0,n);}
            return out.toByteArray();
        }
    }
}
