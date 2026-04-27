# Gitblit-Hack

一款高性能、多线程的 Gitblit 探测与自动化提取工具。

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📖 项目简介

**Gitblit-Hack** 专为安全审计和开发人员设计，能够快速识别并提取 Gitblit 服务器中公开可见的仓库。它通过匿名 RPC 接口自动获取仓库元数据，并提供一键式批量克隆和下载功能。

## ✨ 核心功能

- **匿名情报探测：** 自动通过 `/rpc/` 接口获取仓库名称、大小、最后提交日期以及提交者信息。
- **多线程批量模式：** 支持从文件读取 URL 列表，并发扫描成百上千个目标，并自动导出详细的 CSV 报告。
- **加固提取逻辑：**
    - **克隆模式 (Clone)：** 执行高速 `--depth 1` 浅克隆，仅获取最新快照。
    - **压缩包模式 (Zip)：** 将仓库直接下载为 ZIP 压缩文件。
- **安全与稳定性：**
    - 增强的路径过滤逻辑，解决 Windows/Linux 平台因非法字符导致的保存失败问题。
    - 具备下载大小阈值警告，防止磁盘空间被海量数据撑爆。

## 🚀 安装步骤

1. 克隆本仓库：
   ```bash
   git clone https://github.com/yanxinwu946/Gitblit-Hack.git
   cd Gitblit-Hack
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

## 🛠️ 使用说明

### 1. 单目标探测（仅列出清单）
```bash
python gitblit_hack.py -u http://target.com:9999
```

### 2. 批量扫描（导出 CSV 报告）
准备一个包含目标 URL 的文件（每行一个）：
```bash
python gitblit_hack.py -f targets.txt -t 20
```

### 3. 自动化提取
克隆目标服务器上所有可访问的仓库：
```bash
python gitblit_hack.py -u http://target.com:9999 -m clone
```
或者将所有仓库下载为 ZIP：
```bash
python gitblit_hack.py -u http://target.com:9999 -m zip -l 2.0
```

## ⚙️ 参数说明

| 参数 | 缩写 | 描述 |
| :--- | :--- | :--- |
| `--url` | `-u` | 单个目标 URL，用于探测或提取。 |
| `--file` | `-f` | 包含 URL 列表的文件路径，用于批量扫描。 |
| `--mode` | `-m` | 执行模式：`clone` 或 `zip`。（不选则仅列出详细清单） |
| `--threads` | `-t` | 并发线程数。（默认：10） |
| `--limit` | `-l` | 大小预警阈值，单位 GB。（默认：1.0） |

## ⚠️ 免责声明
本工具仅用于合法授权的安全审计和教育目的。使用者应遵守当地法律法规，开发者不对因误用本工具导致的任何损害或法律责任负责。

---
**作者:** @Sublarge  
**仓库地址:** [https://github.com/yanxinwu946/Gitblit-Hack](https://github.com/yanxinwu946/Gitblit-Hack)