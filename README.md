# 🚀 Squad 战术小队精准抢车工具

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![GitHub Stars](https://img.shields.io/github/stars/tyabase/Squad-Auto-Tool?style=social)

专为《战术小队》(Squad) 游戏开发的精准抢车工具，通过游戏日志事件触发实现毫秒级响应！⚡

## ✨ 核心功能

### 🎯 精准模式升级
- **智能日志监控**：实时分析游戏日志，在载入完成的精确瞬间触发操作
- **事件触发机制**：响应地图加载/阵营加载等关键事件（冷却时间5秒）
- **本地执行日志**：自动生成 `squad_tool.log` 记录所有操作和错误

### 🛠️ 基础功能
- 🖥️ **系统托盘支持**：后台静默运行不打扰
- 🔒 **智能窗口检测**：仅在游戏窗口激活时操作
- 📋 **剪贴板预加载**：自动维护最新命令内容
- 💻 **内置控制台**：实时显示操作状态和触发记录

## ⚠️ 版本更新说明
> 本次更新移除旧版循环模式，全面升级为精准触发模式：
> - 删除：循环建队模式及速度选项
> - 新增：游戏日志事件触发系统
> - 新增：本地日志记录和错误追踪功能

## 📦 安装指南

### 环境要求
- Python 3.8+
- Windows 10/11（需游戏日志读取权限）

```bash
# 克隆仓库
git clone https://github.com/tyabase/Squad-Auto-Tool.git

# 安装依赖
pip install -r requirements.txt

# 运行程序
python squad_tool.py
