# Contributing to Overwatch Assistant

感谢你的贡献！以下是参与项目的指南。

## 如何贡献

### 报告 Bug

- 使用 [Bug Report 模板](.github/ISSUE_TEMPLATE/bug_report.md)
- 提供尽可能详细的复现步骤
- 包含环境信息（OS、Python版本、游戏分辨率等）

### 提出新功能

- 使用 [Feature Request 模板](.github/ISSUE_TEMPLATE/feature_request.md)
- 描述清楚功能需求和预期效果

### 提交代码

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 代码规范

- 使用 Python 3.8+
- 遵循 PEP 8 风格
- 添加适当的注释和文档字符串
- 确保代码通过 `flake8` 检查

## 开发环境

```bash
# 克隆仓库
git clone https://github.com/kfat77/overwatch-assistant.git
cd overwatch-assistant

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装开发依赖
pip install -r requirements.txt
pip install flake8 black pytest
```

## 测试

```bash
# 运行代码检查
flake8 .

# 运行格式化检查
black --check .
```

## 许可证

通过贡献代码，你同意你的贡献将在 MIT 许可证下发布。
