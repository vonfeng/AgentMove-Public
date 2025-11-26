# AgentMove Web Demo

基于大语言模型的零样本下一位置预测交互式演示系统。

## 功能特性

- 🗺️ **交互式地图可视化**: 使用 Leaflet.js 展示轨迹和预测结果
- 🤖 **多模型支持**: 支持 Qwen, Llama, GLM, DeepSeek 等多种 LLM 模型
- 📊 **实时预测**: 可视化展示预测过程和结果
- 🧠 **模块透明**: 显示个人记忆、空间世界、社会知识三大模块的输出
- 🎯 **多种方法**: 支持 AgentMove 完整框架及多个 Baseline 方法

## 快速启动

### 1. 安装依赖

```bash
# 安装主项目依赖（如果还未安装）
pip install -r requirements.txt

# 安装额外的 demo 依赖
pip install -r app/requirements.txt
```

### 2. 配置环境变量

使用 `.env` 文件进行配置（推荐）:

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，添加你的 API keys
nano .env  # 或使用其他编辑器
```

至少需要配置一个 LLM API key:

```bash
# 在 .env 文件中设置（任选其一）
SiliconFlow_API_KEY=your_key_here     # 推荐：提供免费额度
DeepInfra_API_KEY=your_key_here       # 或者使用 DeepInfra
OpenAI_API_KEY=your_key_here          # 或者使用 OpenAI

# Demo 配置（可选，有默认值）
DEMO_HOST=0.0.0.0
DEMO_PORT=8000
DEMO_DEFAULT_CITY=Shanghai
DEMO_DEFAULT_MODEL=qwen2.5-7b
```

**提示**: `.env` 文件已被 `.gitignore` 忽略，不会被提交到代码仓库。

### 3. 准备数据

确保已完成数据预处理流程 (参考主 README):

```bash
# 下载并处理数据
python -m processing.download --data_name=www2019
python -m processing.process_isp_shanghai
# ... 完整的数据处理流程
```

### 4. 启动 Demo

使用启动脚本:

```bash
# 方法 1: 使用启动脚本
bash app/start_demo.sh

# 方法 2: 直接运行
cd app/backend
python api.py
```

### 5. 访问 Demo

打开浏览器访问:

- **Web 界面**: http://localhost:8000
- **API 文档**: http://localhost:8000/api/docs

## 界面说明

### 左侧 - 地图区域

- 显示轨迹的历史移动路径
- 蓝色圆点: 历史轨迹点
- 绿色标记: 真实下一位置
- 红色标记: 预测错误时的预测位置

### 右侧 - 控制面板

1. **配置区**: 选择城市、模型、预测方法
2. **轨迹选择区**: 从数据集中选择或随机选择轨迹
3. **操作区**: 开始预测或加载示例
4. **结果区**: 显示预测结果、推理过程、模块详情

## API 端点

### 核心端点

- `GET /api/health` - 健康检查
- `GET /api/datasets` - 获取可用数据集
- `GET /api/trajectories/{city}` - 获取城市的轨迹列表
- `GET /api/trajectory/{city}/{user_id}/{traj_id}` - 获取轨迹详情
- `POST /api/predict` - 执行预测
- `GET /api/models` - 获取可用模型列表
- `GET /api/example` - 获取示例预测

### 请求示例

```bash
# 健康检查
curl http://localhost:8000/api/health

# 获取轨迹
curl http://localhost:8000/api/trajectories/Shanghai?limit=10

# 执行预测
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "city_name": "Shanghai",
    "model_name": "qwen2.5-7b",
    "platform": "SiliconFlow",
    "prompt_type": "agent_move_v6",
    "user_id": "1",
    "traj_id": "1"
  }'
```

## 架构说明

```
app/
├── backend/
│   ├── api.py              # FastAPI 主应用
│   ├── demo_agent.py       # 简化的 Agent 封装
│   └── config.py           # Demo 配置
├── frontend/
│   ├── index.html          # 主页面
│   └── static/
│       ├── css/style.css   # 样式
│       └── js/main.js      # 前端逻辑
├── start_demo.sh           # 启动脚本
└── README.md              # 本文档
```

## 技术栈

### 后端
- **FastAPI**: 现代化的 Python Web 框架
- **Uvicorn**: ASGI 服务器
- **AgentMove**: 核心预测系统

### 前端
- **Leaflet.js**: 开源地图库
- **原生 JavaScript**: 无框架依赖
- **CSS3**: 现代化样式设计

## 配置选项

编辑 `app/backend/config.py` 来自定义:

```python
DEMO_CONFIG = {
    "host": "0.0.0.0",              # 服务器地址
    "port": 8000,                   # 端口
    "default_city": "Shanghai",     # 默认城市
    "default_model": "qwen2.5-7b",  # 默认模型
    "enable_real_predictions": True, # 启用真实预测
}
```

## 常见问题

### Q: Demo 启动后显示"Demo agent not initialized"?
A: 检查数据是否已预处理完成，确保 `data/processed/` 目录下有对应城市的数据文件。

### Q: 预测请求超时?
A: LLM API 调用可能较慢，特别是使用较大模型时。可以在 `config.py` 中调整超时设置。

### Q: 地图不显示?
A: 检查网络连接，确保可以访问 OpenStreetMap 的地图瓦片服务。

### Q: 如何添加新的城市?
A:
1. 完成该城市的数据预处理
2. 在 `app/backend/config.py` 中添加城市坐标
3. 在前端 `index.html` 的城市选择下拉框中添加选项

### Q: 如何使用本地部署的模型?
A:
1. 使用 vLLM 部署模型 (参考 `serving/vllm_serving.sh`)
2. 配置 `vllm_KEY` 环境变量
3. 在模型选择中选择对应的本地模型

## 性能优化建议

1. **缓存预测结果**: 启用 `cache_predictions` 配置
2. **限制轨迹数量**: 调整 `max_trajectories` 配置
3. **使用更小的模型**: 选择 7B 参数量的模型以获得更快响应
4. **本地模型部署**: 使用 vLLM 在本地部署模型避免网络延迟

## 开发调试

### 启用开发模式

```bash
# 自动重载模式
uvicorn app.backend.api:app --reload --host 0.0.0.0 --port 8000
```

### 查看日志

后端日志会输出到控制台，包括:
- API 请求信息
- Agent 初始化状态
- 预测执行日志
- 错误信息

### 前端调试

打开浏览器开发者工具 (F12):
- Console: 查看 JavaScript 日志
- Network: 监控 API 请求
- Elements: 检查 DOM 结构

## 许可证

本 demo 遵循主项目的许可证。

## 引用

如果您使用了本 demo 系统，请引用 AgentMove 论文:

```bibtex
@inproceedings{feng2025agentmove,
  title={Agentmove: A large language model based agentic framework for zero-shot next location prediction},
  author={Feng, Jie and Du, Yuwei and Zhao, Jie and Li, Yong},
  booktitle={Proceedings of the 2025 Conference of the Nations of the Americas Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)},
  pages={1322--1338},
  year={2025}
}
```
