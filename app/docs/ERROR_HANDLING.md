# 错误处理改进说明

## 问题

之前 demo 的 predict 端点失败时，只显示简单的 500 错误，没有详细的错误信息：
```
INFO:     127.0.0.1:42032 - "POST /api/predict HTTP/1.1" 500 Internal Server Error
```

## 改进内容

### 1. 后端改进 ([app/backend/api.py](app/backend/api.py))

#### 添加详细日志记录

```python
import logging
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

#### 增强的错误处理

所有 API 端点现在都包含：

1. **请求日志记录**
   ```python
   logger.info(f"Prediction request: city={request.city_name}, user={request.user_id}, ...")
   ```

2. **详细的错误日志**
   ```python
   logger.error(f"Prediction failed: {e}")
   logger.error(f"Error type: {type(e).__name__}")
   logger.error(f"Full traceback:\n{traceback.format_exc()}")
   ```

3. **结构化的错误响应**
   ```python
   return JSONResponse(
       status_code=500,
       content={
           "success": False,
           "error": str(e),
           "error_type": type(e).__name__,
           "details": {
               "traceback": traceback.format_exc(),
               "request": {...}
           },
           "message": "Prediction failed. Check server logs for details."
       }
   )
   ```

### 2. 前端改进 ([app/frontend/static/js/main.js](app/frontend/static/js/main.js))

#### 更好的错误显示

```javascript
// 显示详细错误信息
let errorMessage = '预测失败\n\n';
if (data.error) errorMessage += `错误: ${data.error}\n`;
if (data.error_type) errorMessage += `类型: ${data.error_type}\n`;
if (data.message) errorMessage += `\n${data.message}\n`;
if (data.details && data.details.traceback) {
    errorMessage += `\n详细堆栈:\n${data.details.traceback.substring(0, 500)}...`;
}

// 在控制台输出完整信息
console.error('Prediction failed with details:', data);

// 显示 alert 给用户
alert(errorMessage);
```

### 3. 启动时的错误处理

```python
@app.on_event("startup")
async def startup_event():
    global demo_agent
    try:
        logger.info("Initializing demo agent...")
        demo_agent = DemoAgent(...)
        logger.info("✓ Demo agent initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize demo agent: {e}")
        logger.error(traceback.format_exc())
        print(f"  Error details: {traceback.format_exc()}")
```

## 现在的错误信息示例

### 服务器日志

```
2025-01-26 22:15:30 - app.backend.api - INFO - Initializing demo agent...
2025-01-26 22:15:31 - app.backend.api - INFO - Prediction request: city=Shanghai, user=3427331, traj=0, model=qwen2.5-7b, platform=SiliconFlow, prompt_type=agent_move_v6
2025-01-26 22:15:32 - app.backend.api - ERROR - Prediction failed: No module named 'xxxx'
2025-01-26 22:15:32 - app.backend.api - ERROR - Error type: ModuleNotFoundError
2025-01-26 22:15:32 - app.backend.api - ERROR - Full traceback:
Traceback (most recent call last):
  File "/data5/fengjie/AgentMove-Public/app/backend/api.py", line 186, in predict_next_location
    result = demo_agent.predict(...)
  ...
ModuleNotFoundError: No module named 'xxxx'
```

### 用户界面

弹出对话框显示：
```
预测失败

错误: No module named 'xxxx'
类型: ModuleNotFoundError

Prediction failed. Check server logs for details.

详细堆栈:
Traceback (most recent call last):
  File "/data5/fengjie/AgentMove-Public/app/backend/api.py", line 186...
```

### 浏览器控制台

```javascript
Prediction failed with details: {
  success: false,
  error: "No module named 'xxxx'",
  error_type: "ModuleNotFoundError",
  details: {
    traceback: "...",
    request: {...}
  },
  message: "Prediction failed. Check server logs for details."
}
```

## 测试

运行测试脚本验证改进：
```bash
python app/test_error_handling.py
```

## 调试建议

当遇到错误时：

1. **查看服务器日志** - 包含完整的 traceback 和上下文信息
2. **查看浏览器控制台** - 查看请求/响应的详细信息
3. **查看弹出的 alert** - 快速了解错误类型和原因

## 改进的文件

- `app/backend/api.py` - 添加日志记录和详细错误处理
- `app/frontend/static/js/main.js` - 改进前端错误显示
- `app/test_error_handling.py` - 测试脚本（新增）

## 注意事项

- 所有错误信息都会在服务器日志中记录，包括完整的 traceback
- 前端会显示用户友好的错误消息，同时在控制台输出详细信息
- 生产环境可能需要调整日志级别或隐藏部分敏感信息
