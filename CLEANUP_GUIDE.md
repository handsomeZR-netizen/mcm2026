# 工作区清理指南

## ✅ 可以直接删除（临时文件/调试文件）

这些文件是临时生成的，对最终论文没有用处：

### 根目录临时文件
```
temp_continue.txt                    # 临时文本文件
test_star_fix.py                     # 测试脚本
fix_data_archaeology_plot.py         # 临时修复脚本
fix_numpy_and_generate.bat           # 临时批处理文件
generate_pro_buff_enhanced.py        # 临时图表生成脚本（已集成到主代码）
ABC_Flow_Diagram_Prompt.md          # AI绘图prompt（已使用完毕）
图表修复说明.md                      # 临时说明文档
```

**删除命令：**
```cmd
del temp_continue.txt test_star_fix.py fix_data_archaeology_plot.py fix_numpy_and_generate.bat generate_pro_buff_enhanced.py ABC_Flow_Diagram_Prompt.md 图表修复说明.md
```

### 归档的旧图表（已被新版本替代）
```
figures/_archive/                    # 整个文件夹（25个旧版本图表）
```

**删除命令：**
```cmd
rmdir /s /q figures\_archive
```

### 归档的旧数据
```
data/processed/_archive/             # 整个文件夹
```

**删除命令：**
```cmd
rmdir /s /q data\processed\_archive
```

---

## 🤔 可选删除（根据需要保留）

### 1. 历史版本文件夹（如果不需要回溯）
```
历史版本/                           # 包含早期思路和草稿
  ├── GAM公式推导.docx
  ├── 第一题完整.md
  ├── 第一题完整.pdf
  ├── 第一题思路改进.md
  ├── 第三题完整思路.md
  ├── 第二题思路v1.md
  ├── 第二题解答.docx
  └── 美赛建议来自去年的o奖论文.md
```

**建议：** 如果你已经完成论文，这些历史版本可以删除。如果想保留作为参考，可以压缩后保留。

**删除命令：**
```cmd
rmdir /s /q 历史版本
```

### 2. 画图示例文件夹
```
画图示例/
  └── seaborn示例.md
```

**建议：** 如果你已经掌握绘图技巧，可以删除。

**删除命令：**
```cmd
rmdir /s /q 画图示例
```

### 3. 中间文档（已整合到最终报告）
```
Task2_Scorecard_Fix_Complete.md      # Task2修复记录
Task3_O_Prize_Enhancements.md        # Task3优化记录
O_Prize_Implementation_Guide.md      # O奖实施指南
O_Prize_Integration_Complete.md      # O奖整合完成记录
O_Prize_Final_Checklist.md           # O奖最终检查清单
```

**建议：** 这些是开发过程文档。如果最终报告已完成，可以删除。如果想保留开发记录，建议移到 `docs/` 文件夹。

**删除命令：**
```cmd
del Task2_Scorecard_Fix_Complete.md Task3_O_Prize_Enhancements.md O_Prize_Implementation_Guide.md O_Prize_Integration_Complete.md O_Prize_Final_Checklist.md
```

### 4. 快速参考文档（如果已熟悉）
```
Task2_Quick_Reference.md
Task3_Quick_Reference.md
Task4_Quick_Reference.md
Task2_README.md
Task3_README.md
Task4_README.md
```

**建议：** 这些是快速查阅文档。如果你已经完成所有任务，可以删除。

**删除命令：**
```cmd
del Task2_Quick_Reference.md Task3_Quick_Reference.md Task4_Quick_Reference.md Task2_README.md Task3_README.md Task4_README.md
```

### 5. 原始题目文件（如果已备份）
```
C题.md                               # 题目markdown版本
C题.pdf                              # 题目PDF版本（保留一个即可）
```

**建议：** 保留 PDF 版本，删除 markdown 版本。

**删除命令：**
```cmd
del C题.md
```

### 6. 数据压缩包（如果已解压）
```
data_part1.zip                       # 原始数据压缩包
```

**建议：** 如果 `data/raw/` 和 `data/processed/` 已有所有数据，可以删除压缩包节省空间。

**删除命令：**
```cmd
del data_part1.zip
```

### 7. Summary PDF文件（如果有最终报告）
```
Task2_Summary.pdf
Task3_Summary.pdf
Task4_Summary.pdf
```

**建议：** 如果这些是中间总结，且最终报告 `paper_package_Q1-4/Report_Q1-4_Enhanced_zh.pdf` 已包含所有内容，可以删除。

**删除命令：**
```cmd
del Task2_Summary.pdf Task3_Summary.pdf Task4_Summary.pdf
```

### 8. 空文件夹
```
notebooks/                           # 如果为空
outputs/                             # 检查是否还需要
```

**检查命令：**
```cmd
dir notebooks
dir outputs
```

---

## 🔒 必须保留的文件

### 核心论文文件
```
paper_package_Q1-4/                  # 最终提交包
  ├── Report_Q1-4_Enhanced_zh.md
  ├── Report_Q1-4_Enhanced_zh.pdf
  ├── Report_Q1-4_Enhanced_zh.docx
  └── figures/                       # 论文使用的所有图表
```

### 核心代码
```
src/                                 # 所有Python脚本
data/raw/                            # 原始数据
data/processed/                      # 处理后的数据（非_archive）
figures/                             # 最新版本的图表（非_archive）
```

### 重要文档
```
README.md                            # 项目说明
README_O_Prize.md                    # O奖策略说明
DECISIONS.md                         # 关键决策记录
DONE.md                              # 完成记录
Project_Documentation_Index.md       # 文档索引
GAM_Math_Summary.md                  # GAM数学总结
```

### 配置文件
```
.gitignore                           # Git配置
.kiro/                               # Kiro配置
```

---

## 📊 清理后的预期结构

```
mcm代码/
├── .kiro/                           # 配置
├── data/
│   ├── raw/                         # 原始数据
│   └── processed/                   # 处理后数据
├── figures/                         # 最新图表
├── src/                             # 所有代码
├── paper/                           # 论文草稿（可选保留）
├── paper_package_Q1-4/              # 最终提交包 ⭐
├── README.md
├── README_O_Prize.md
├── DECISIONS.md
├── DONE.md
├── Project_Documentation_Index.md
└── GAM_Math_Summary.md
```

---

## 🚀 一键清理脚本

### 保守清理（只删除明确的临时文件）
```cmd
@echo off
echo 清理临时文件...
del temp_continue.txt test_star_fix.py fix_data_archaeology_plot.py 2>nul
del fix_numpy_and_generate.bat generate_pro_buff_enhanced.py 2>nul
del ABC_Flow_Diagram_Prompt.md 图表修复说明.md 2>nul
rmdir /s /q figures\_archive 2>nul
rmdir /s /q data\processed\_archive 2>nul
echo 清理完成！
pause
```

### 激进清理（删除所有可选文件）
```cmd
@echo off
echo 警告：这将删除所有历史版本和中间文档！
pause
del temp_continue.txt test_star_fix.py fix_data_archaeology_plot.py 2>nul
del fix_numpy_and_generate.bat generate_pro_buff_enhanced.py 2>nul
del ABC_Flow_Diagram_Prompt.md 图表修复说明.md 2>nul
del C题.md data_part1.zip 2>nul
del Task2_Scorecard_Fix_Complete.md Task3_O_Prize_Enhancements.md 2>nul
del O_Prize_Implementation_Guide.md O_Prize_Integration_Complete.md 2>nul
del O_Prize_Final_Checklist.md 2>nul
del Task2_Quick_Reference.md Task3_Quick_Reference.md Task4_Quick_Reference.md 2>nul
del Task2_README.md Task3_README.md Task4_README.md 2>nul
del Task2_Summary.pdf Task3_Summary.pdf Task4_Summary.pdf 2>nul
rmdir /s /q figures\_archive 2>nul
rmdir /s /q data\processed\_archive 2>nul
rmdir /s /q 历史版本 2>nul
rmdir /s /q 画图示例 2>nul
echo 清理完成！
pause
```

---

## 💾 预估节省空间

- **临时文件**: ~1-2 MB
- **归档图表**: ~15-20 MB
- **历史版本**: ~5-10 MB
- **数据压缩包**: ~10-50 MB（如果删除）
- **总计**: 约 30-80 MB

---

## ⚠️ 注意事项

1. **删除前备份**：建议先将整个项目文件夹压缩备份
2. **检查依赖**：确保 `paper_package_Q1-4/` 中的所有图片引用都正确
3. **Git提交**：如果使用Git，先提交当前状态再清理
4. **最终提交**：确保 `paper_package_Q1-4/` 包含所有需要提交的文件

---

## 📝 建议的清理顺序

1. ✅ 先删除明确的临时文件（保守清理）
2. 🔍 检查 `paper_package_Q1-4/` 是否完整
3. 📦 备份整个项目
4. 🗑️ 根据需要删除可选文件
5. ✅ 验证最终报告能正常打开和显示所有图表
