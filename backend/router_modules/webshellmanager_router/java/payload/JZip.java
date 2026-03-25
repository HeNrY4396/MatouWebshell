// Source code is decompiled from a .class file using FernFlower decompiler.
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

/**
 * 一个用于执行 zip 和 unzip 操作的工具类。
 * 这个类使用了一种非常规的方法，即通过 `equals` 方法传递参数，
 * 并通过 `run` 或 `toString` 方法执行主要逻辑。
 */
public class JZip {
    /**
     * 一个用于存储操作参数的 HashMap。
     * 它是通过转换传递给 `equals` 方法的对象来填充的。
     */
    private HashMap parameterMap;

    /**
     * 默认构造函数。
     */
    public JZip() {
    }

    /**
     * 将多个源文件或目录压缩成一个 zip 文件。
     * @param zipFileName 目标 zip 文件的完整路径和名称。
     * @param sourcePaths 要压缩的源文件或目录的路径，用 "|" 分隔。
     * @return 处理的文件和目录总数。
     * @throws Exception 如果发生 I/O 错误。
     */
    public int zipMultiple(String zipFileName, String sourcePaths) throws Exception {
        // 创建一个 ZipOutputStream，用于将数据写入 zip 文件。
        ZipOutputStream zipOutputStream = new ZipOutputStream(new FileOutputStream(zipFileName));
        
        // 按分隔符拆分路径
        String[] paths = sourcePaths.split("\\|");
        int totalFiles = 0;
        
        for (int i = 0; i < paths.length; i++) {
            String path = paths[i].trim();
            if (path.length() == 0) continue; // 跳过空路径
            
            File sourceFile = new File(path);
            if (!sourceFile.exists()) {
                continue; // 跳过不存在的文件/目录
            }
            
            // 获取当前路径下所有待压缩的文件和目录的列表
            List fileList = getAllFiles(sourceFile);
            Iterator iterator = fileList.iterator();
            
            while (iterator.hasNext()) {
                File file = (File)iterator.next();
                
                // 计算相对路径，保持目录结构
                String relativePath;
                if (sourceFile.isFile()) {
                    // 如果源是文件，直接使用文件名
                    relativePath = sourceFile.getName();
                } else {
                    // 如果源是目录，使用目录名作为前缀
                    relativePath = sourceFile.getName() + "/" + getRelativePath(path, file);
                }
                
                if (file.isFile()) {
                    // 创建一个新的 zip 条目
                    zipOutputStream.putNextEntry(new ZipEntry(relativePath));
                    
                    // 创建文件输入流以读取文件内容
                    InputStream inputStream = new FileInputStream(file);
                    byte[] temp = new byte[10240];
                    int readNum;
                    
                    // 从文件中读取数据到缓冲区，然后写入 zip 输出流
                    while ((readNum = inputStream.read(temp, 0, temp.length)) != -1) {
                        zipOutputStream.write(temp, 0, readNum);
                    }
                    
                    // 关闭当前文件的输入流
                    inputStream.close();
                } else if (file.isDirectory()) {
                    // 为目录创建一个条目（确保路径以/结尾）
                    if (!relativePath.endsWith("/")) {
                        relativePath += "/";
                    }
                    zipOutputStream.putNextEntry(new ZipEntry(relativePath));
                }
                
                totalFiles++;
            }
        }
        
        // 强制将缓冲区中的任何剩余数据写入流
        zipOutputStream.flush();
        // 完成 zip 文件的创建并关闭流
        zipOutputStream.close();
        
        return totalFiles;
    }

    /**
     * 将源文件或目录压缩成一个 zip 文件。
     * @param zipFileName 目标 zip 文件的完整路径和名称。
     * @param sourceFileName 要压缩的源文件或目录的完整路径。
     * @return 处理的文件和目录总数。
     * @throws Exception 如果发生 I/O 错误。
     */
    public int zip(String zipFileName, String sourceFileName) throws Exception {
        // 检查是否包含多个路径（通过"|"分隔符判断）
        if (sourceFileName.contains("|")) {
            return zipMultiple(zipFileName, sourceFileName);
        }
        
        // 原有的单路径压缩逻辑
        ZipOutputStream zipOutputStream = new ZipOutputStream(new FileOutputStream(zipFileName));
        List fileList = getAllFiles(new File(sourceFileName));
        Iterator iterator = fileList.iterator();
        File file = null;
        InputStream inputStream = null;
        byte[] temp = new byte[10240];
        int readNum;

        while(true) {
            while(iterator.hasNext()) {
                file = (File)iterator.next();
                if (file.isFile()) {
                    zipOutputStream.putNextEntry(new ZipEntry(getRelativePath(sourceFileName, file)));
                    inputStream = new FileInputStream(file);

                    while((readNum = inputStream.read(temp, 0, temp.length)) != -1) {
                        zipOutputStream.write(temp, 0, readNum);
                    }

                    inputStream.close();
                } else {
                    zipOutputStream.putNextEntry(new ZipEntry(getRelativePath(sourceFileName, file)));
                }
            }

            zipOutputStream.flush();
            zipOutputStream.close();
            return fileList.size();
        }
    }

    /**
     * 从给定的源目录中递归获取所有文件和子目录。
     * @param srcFile 源文件或目录。
     * @return 一个包含 File 对象的列表。
     */
    private static List getAllFiles(File srcFile) {
        // 创建一个列表来存储找到的所有文件和目录。
        List fileList = new ArrayList();
        
        // 检查输入是否为文件
        if (srcFile.isFile()) {
            // 如果是文件，直接添加到列表中
            fileList.add(srcFile);
            return fileList;
        }
        
        // 如果是目录，获取目录下的所有文件和子目录。
        File[] tmp = srcFile.listFiles();
        
        // 检查 listFiles() 的返回值是否为 null（可能由于权限问题或其他原因）
        if (tmp == null) {
            // 如果无法读取目录内容，返回空列表
            return fileList;
        }

        // 遍历目录内容。
        for(int i = 0; i < tmp.length; ++i) {
            // 如果是文件，直接将其添加到列表中。
            if (tmp[i].isFile()) {
                fileList.add(tmp[i]);
            }

            // 如果是目录，则需要进一步处理。
            if (tmp[i].isDirectory()) {
                // 递归调用此方法以获取其内容
                fileList.addAll(getAllFiles(tmp[i]));
                // 同时添加目录本身（保持目录结构）
                fileList.add(tmp[i]);
            }
        }

        // 返回包含所有文件和目录的列表。
        return fileList;
    }

    /**
     * 计算文件相对于基本目录路径的相对路径。
     * 这用于在 zip 文件中维护目录结构。
     * @param dirPath 基本目录路径。
     * @param file 需要计算相对路径的文件。
     * @return 相对路径字符串。
     */
    private static String getRelativePath(String dirPath, File file) {
        // 将基本目录路径字符串转换为 File 对象。
        File dir = new File(dirPath);
        // 初始化相对路径为文件名本身。
        String relativePath = file.getName();

        // 循环向上遍历文件的父目录，构建相对路径。
        while(true) {
            // 获取当前文件的父目录。
            file = file.getParentFile();
            // 如果父目录为 null 或等于基本目录，说明已经到达顶层，停止循环。
            if (file == null || file.equals(dir)) {
                return relativePath;
            }

            // 将父目录的名称和路径分隔符前置到当前相对路径上。
            relativePath = file.getName() + "/" + relativePath;
        }
    }

    /**
     * 从 zip 文件中提取文件和目录。
     * @param zipFileName 源 zip 文件的完整路径。
     * @param sourceFileName 文件将被提取到的目标目录。
     * @return zip 文件中的总条目数。
     * @throws Exception 如果发生 I/O 错误。
     */
    public int unZip(String zipFileName, String sourceFileName) throws Exception {
        // 打开 zip 文件以供读取。
        ZipFile zipFile = new ZipFile(zipFileName);
        // 获取 zip 文件中所有条目（文件和目录）的枚举。
        Enumeration enumeration = zipFile.entries();
        ZipEntry zipEntry = null;
        File file = null;
        File dirFile = null;
        // 创建一个缓冲区，用于在 zip 流和文件之间传输数据。
        byte[] tmp = new byte[10240];
        InputStream inputStream = null;
        OutputStream outputStream = null;

        while(true) {
            int readNum;
            // 遍历 zip 文件中的所有条目。
            while(enumeration.hasMoreElements()) {
                zipEntry = (ZipEntry)enumeration.nextElement();
                // 检查条目是否为目录。
                if (zipEntry.isDirectory()) {
                    // 构建目标目录的路径并创建目录（包括任何必要的父目录）。
                    dirFile = new File(sourceFileName + "/" + zipEntry.getName());
                    dirFile.mkdirs();
                } else { // 如果条目是文件。
                    // 构建目标文件的完整路径。
                    file = new File(sourceFileName + "/" + zipEntry.getName());
                    // 获取文件的父目录并确保它存在。
                    dirFile = file.getParentFile();
                    dirFile.mkdirs();
                    // 获取该 zip 条目的输入流。
                    inputStream = zipFile.getInputStream(zipEntry);
                    // 创建一个文件输出流，将数据写入磁盘上的文件。
                    outputStream = new FileOutputStream(file);

                    // 从 zip 条目读取数据到缓冲区，然后写入文件输出流。
                    while((readNum = inputStream.read(tmp, 0, tmp.length)) != -1) {
                        outputStream.write(tmp, 0, readNum);
                    }

                    // 关闭当前文件的输入和输出流。
                    inputStream.close();
                    outputStream.flush();
                    outputStream.close();
                }
            }

            // 获取 zip 文件中的总条目数。
            readNum = zipFile.size();
            // 关闭 zip 文件，释放资源。
            zipFile.close();
            // 返回提取的条目总数。
            return readNum;
        }
    }

    /**
     * 一个非常规的 toString 实现。它通过 `run()` 触发主要逻辑，
     * 将结果存储在参数映射中，然后将该映射置为 null。
     * @return 总是返回 null。
     */
    public String toString() {
        // 调用 run() 方法执行核心操作，并将返回的字符串结果转换为字节数组。
        this.parameterMap.put("result", this.run().getBytes());
        // 清除参数映射，可能为了垃圾回收或防止重用。
        this.parameterMap = null;
        // 按照约定返回 null。
        return null;
    }

    /**
     * 一个非常规的 equals 实现。它不检查相等性，
     * 而是用此方法作为向对象传递参数的方式，通过设置内部的 parameterMap。
     * @param paramObject 一个预期为 HashMap 的对象。
     * @return 如果参数映射设置成功，则返回 true，否则返回 false。
     */
    public boolean equals(Object paramObject) {
        try {
            // 将传入的对象强制转换为 HashMap，并赋值给实例变量 parameterMap。
            this.parameterMap = (HashMap)paramObject;
            // 表示参数设置成功。
            return true;
        } catch (Exception var3) {
            // 如果转换失败（例如，paramObject 不是 HashMap），则捕获异常。
            return false;
        }
    }

    /**
     * 类的主执行逻辑。它从 `parameterMap` 读取参数
     * 来决定执行 zip 还是 unzip 操作。
     * @return 一个指示操作结果的字符串。
     */
    public String run() {
        try {
            // 从参数映射中获取要执行的方法名（"zip" 或 "unZip"）。
            String methodName = this.get("methodName");
            // 从参数映射中获取压缩/解压的文件名。
            String filename = this.get("compressFile");
            // 从参数映射中获取压缩/解压的目录路径。
            String dirPath = this.get("compressDir");
            // 检查方法名是否存在。
            if (methodName != null) {
                // 检查文件名和目录路径是否存在。
                if (filename != null && dirPath != null) {
                    // 如果方法是 "zip"。
                    if ("zip".equals(methodName)) {
                        // 执行 zip 操作并返回格式化的成功信息。
                        return String.format("ok fileNum: %s >> %s", new Integer(this.zip(filename, dirPath)), filename);
                    } else {
                        // 否则，检查方法是否是 "unZip"。
                        // 使用三元运算符进行判断。
                        return "unZip".equals(methodName) ? String.format("ok fileNum: %s >> %s", new Integer(this.unZip(filename, dirPath)), dirPath) : "JZip: NoMethod";
                    }
                } else {
                    // 如果缺少文件名或目录路径，返回错误信息。
                    return "compressFile or compressDir is null";
                }
            } else {
                // 如果缺少方法名，返回错误信息。
                return "methodName is null";
            }
        } catch (Exception var4) {
            // 如果在执行过程中发生任何异常，捕获并返回异常信息。
            return var4.getMessage();
        }
    }

    /**
     * 从参数映射中检索一个值，并将其从字节数组转换为字符串。
     * @param key 所需值的键。
     * @return 值的字符串形式，如果发生错误或找不到键，则返回 null。
     */
    public String get(String key) {
        try {
            // 从 parameterMap 获取与键关联的值（预期为 byte[]），并创建一个新的字符串。
            return new String((byte[])this.parameterMap.get(key));
        } catch (Exception var3) {
            // 如果获取或转换时发生异常，返回 null。
            return null;
        }
    }

    /**
     * 直接从参数映射中检索一个字节数组值。
     * @param key 所需值的键。
     * @return 值的字节数组形式，如果发生错误或找不到键，则返回 null。
     */
    public byte[] getByteArray(String key) {
        try {
            // 从 parameterMap 获取与键关联的值，并将其强制转换为 byte[]。
            return (byte[])this.parameterMap.get(key);
        } catch (Exception var3) {
            // 如果获取或转换时发生异常，返回 null。
            return null;
        }
    }
}