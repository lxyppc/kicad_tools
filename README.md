# KiCAD生产文件生成器

使用方法:

1 复制mf_tool.py到"[KiCad安装目录]\share\kicad\scripting\plugins" 路径下

2 在KiCAD的Python命令行窗口中键入下列命令
```python
import mf_tool as mf
mf.GenMFDoc()
```
3 BOM文件和位置文件会以CSV格式存放在电路板相同目录下

## 注意:

GenMFDoc() 会改变电路板的钻孔原点。建议先用GenMFDoc()生成BOM文件和位置文件，再生成Gerber文件。

生成的BOM文件和坐标文件可以直接在sz-jlc.com进行贴装


# Manufacture Tools for kicad

Usage:

step 1: Copy the mf_tool.py to “[kicad install path]\share\kicad\scripting\plugins”

step 2: In Python console window, type 
```python
import mf_tool as mf
mf.GenMFDoc()
```

step 3: the BOM and Postion CSV file will be generated under the same folder of the board file

## Attention:

The GenMFDoc() command will change the Aux original point