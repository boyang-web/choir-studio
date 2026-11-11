package cn.hesheng.choirstudio;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

/** Read-only, bounded HTTP transport shared by the Android service and host-side tests. */
public final class RelayHttpServer implements Closeable {
    public interface Opener {InputStream open() throws Exception;}
    public static final class Resource {
        final long size;final Opener opener;
        public Resource(long size,Opener opener){this.size=size;this.opener=opener;}
    }
    private final ServerSocket listener;
    private final byte[] envelope,landing;
    private final Map<String,Resource> files;
    private final Resource apk;
    private final boolean allowLoopback;
    private volatile boolean closed=false;
    private final Set<Socket> clients=Collections.synchronizedSet(new HashSet<>());
    private final ThreadPoolExecutor pool=new ThreadPoolExecutor(3,3,0L,TimeUnit.SECONDS,new ArrayBlockingQueue<>(8),r->{Thread t=new Thread(r,"choir-share-client");t.setDaemon(true);return t;});
    public RelayHttpServer(int port,byte[] envelope,Map<String,Resource> files,Resource apk,String landing,boolean allowLoopback)throws IOException{
        this.envelope=envelope.clone();this.files=new HashMap<>(files);this.apk=apk;this.landing=landing.getBytes(StandardCharsets.UTF_8);this.allowLoopback=allowLoopback;
        listener=new ServerSocket();listener.setReuseAddress(true);listener.bind(new InetSocketAddress(port));
        Thread accept=new Thread(this::accept,"choir-share-listen");accept.setDaemon(true);accept.start();
    }
    public int port(){return listener.getLocalPort();}
    private void accept(){
        while(!closed){try{
            Socket client=listener.accept();
            InetAddress peer=client.getInetAddress();
            if(!(peer instanceof Inet4Address) || !(peer.isSiteLocalAddress() || (allowLoopback&&peer.isLoopbackAddress()))){client.close();continue;}
            client.setSoTimeout(6000);clients.add(client);
            try{pool.execute(()->serve(client));}catch(RejectedExecutionException full){clients.remove(client);client.close();}
        }catch(IOException error){if(!closed)try{close();}catch(IOException ignored){}}}
    }
    private void serve(Socket client){
        try(Socket socket=client){
            InputStream input=socket.getInputStream();ByteArrayOutputStream header=new ByteArrayOutputStream();int b,match=0;
            byte[] delimiter={13,10,13,10};
            while((b=input.read())!=-1){
                header.write(b);if(header.size()>8192){respond(socket,431,"text/plain",new byte[0],false);return;}
                match=b==delimiter[match]?match+1:(b==13?1:0);if(match==4)break;
            }
            if(match!=4){respond(socket,400,"text/plain",new byte[0],false);return;}
            String first=new String(header.toByteArray(),StandardCharsets.US_ASCII).split("\r\n",2)[0];String[] request=first.split(" ");
            if(request.length!=3 || !request[2].matches("HTTP/1\\.[01]")){respond(socket,400,"text/plain",new byte[0],false);return;}
            boolean head=request[0].equals("HEAD");
            if(!head&&!request[0].equals("GET")){respond(socket,405,"text/plain",new byte[0],false);return;}
            String path=request[1];
            if(path.equals("/")){respond(socket,200,"text/html; charset=utf-8",landing,head);return;}
            if(path.equals("/local-update/manifest")){respond(socket,200,"application/json",envelope,head);return;}
            Resource resource=null;String type="application/octet-stream";
            if(path.equals("/download/choir-studio.apk")){resource=apk;type="application/vnd.android.package-archive";}
            else if(path.matches("/local-update/files/[a-f0-9]{64}"))resource=files.get(path.substring("/local-update/files/".length()));
            if(resource==null){respond(socket,404,"text/plain",new byte[0],head);return;}
            try(InputStream data=resource.opener.open()){
                OutputStream out=socket.getOutputStream();headers(out,200,type,resource.size);
                if(!head){byte[] buffer=new byte[65536];long remaining=resource.size;int n;
                    while(remaining>0&&(n=data.read(buffer,0,(int)Math.min(buffer.length,remaining)))!=-1){out.write(buffer,0,n);remaining-=n;}
                }
                out.flush();
            }
        }catch(Exception ignored){/* Receiver keeps the old version if a transfer fails. */}
        finally{clients.remove(client);}
    }
    private static void headers(OutputStream out,int code,String type,long size)throws IOException{
        String disposition=type.startsWith("application/vnd.android")?"Content-Disposition: attachment; filename=\"choir-studio.apk\"\r\n":"";
        out.write(("HTTP/1.1 "+code+" "+(code==200?"OK":"Error")+"\r\nContent-Type: "+type+"\r\nContent-Length: "+size+"\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n"+disposition+"\r\n").getBytes(StandardCharsets.US_ASCII));
    }
    private static void respond(Socket socket,int code,String type,byte[] bytes,boolean head)throws IOException{
        OutputStream out=socket.getOutputStream();headers(out,code,type,bytes.length);if(!head)out.write(bytes);out.flush();
    }
    @Override public void close()throws IOException{
        closed=true;listener.close();pool.shutdownNow();
        synchronized(clients){for(Socket client:clients)try{client.close();}catch(IOException ignored){}clients.clear();}
    }
}
