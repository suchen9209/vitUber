"""
Flask 服务端 - 直播间里程碑展示
完全独立运行，与现有系统通过 HTTP API 交互
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径（如果需要导入其他模块）
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import time

from data_store import get_data_store, MilestoneDataStore

# Flask 应用配置
app = Flask(__name__, 
    template_folder='templates',
    static_folder='static'
)
app.config['SECRET_KEY'] = 'vituber-milestone-secret-key'

# 启用跨域
CORS(app)

# WebSocket
socketio = SocketIO(app, 
    cors_allowed_origins="*",
    async_mode='threading',
    logger=False,  # 生产环境关闭日志
    engineio_logger=False
)

# 获取数据存储
data_store = get_data_store()


def broadcast_event(event_data: dict):
    """广播事件给所有连接的客户端"""
    try:
        socketio.server.emit('live_event', event_data, namespace='/')
        
        # 如果有升级，额外广播升级事件
        if event_data.get('level_up'):
            socketio.server.emit('level_up', event_data['level_up'], namespace='/')
            
    except Exception as e:
        print(f"[Flask] 广播失败: {e}")


# 注册数据监听器
data_store.add_listener(broadcast_event)


# ============ 路由定义 ============

@app.route('/')
def index():
    """主页面 - OBS背景"""
    return render_template('background.html')


@app.route('/simple')
def simple():
    """简化版背景（如果完整版有问题用这个）"""
    return render_template('simple.html')


@app.route('/api/status')
def api_status():
    """REST API: 获取当前状态"""
    return jsonify(data_store.get_status())


@app.route('/api/event', methods=['POST'])
def api_event():
    """
    REST API: 触发事件
    
    请求体:
    {
        "type": "enter|chat|gift|like|share",
        "user": "用户名",
        "extra": {}  // 可选
    }
    """
    try:
        data = request.get_json() or {}
        event_type = data.get('type', 'chat')
        user = data.get('user', '')
        extra = data.get('extra', {})
        
        result = data_store.add_event(event_type, user, extra)
        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/mock', methods=['POST'])
def api_mock():
    """
    模拟数据（测试用）
    
    请求体:
    {
        "enters": 10,
        "chats": 50,
        "gifts": 5
    }
    """
    try:
        data = request.get_json() or {}
        
        # 批量添加模拟事件
        for _ in range(data.get('enters', 0)):
            data_store.add_event('enter', f'用户{hash(time.time()) % 10000}')
            time.sleep(0.01)
            
        for _ in range(data.get('chats', 0)):
            data_store.add_event('chat', f'用户{hash(time.time()) % 10000}')
            time.sleep(0.01)
            
        for _ in range(data.get('gifts', 0)):
            data_store.add_event('gift', f'大佬{hash(time.time()) % 10000}')
            time.sleep(0.01)
        
        return jsonify({
            "success": True,
            "status": data_store.get_status()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/reset', methods=['POST'])
def api_reset():
    """重置今日数据（调试用）"""
    data_store.reset_today()
    return jsonify({"success": True, "message": "今日数据已重置"})


@app.route('/api/reset_all', methods=['POST'])
def api_reset_all():
    """重置所有数据（危险！调试用）"""
    data_store.reset_all()
    return jsonify({"success": True, "message": "所有数据已重置"})


# ============ WebSocket 事件 ============

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    print(f'[Flask] 客户端已连接: {request.sid}')
    # 发送当前状态
    emit('init_data', data_store.get_status())


@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    print(f'[Flask] 客户端断开: {request.sid}')


@socketio.on('request_update')
def handle_request_update():
    """客户端请求更新"""
    emit('init_data', data_store.get_status())


# ============ 启动函数 ============

def start_server(host='0.0.0.0', port=8080, debug=False):
    """
    启动服务器
    
    Args:
        host: 绑定地址，默认0.0.0.0允许外部访问
        port: 端口，默认5000
        debug: 调试模式
    """
    print(f"""
╔═══════════════════════════════════════════════════╗
║                                                   ║
║   🎮 vitUber 里程碑系统 Flask 服务端              ║
║                                                   ║
║   📍 访问地址: http://{host}:{port}              ║
║                                                   ║
║   📊 OBS浏览器源: http://localhost:{port}         ║
║                                                   ║
╚═══════════════════════════════════════════════════╝
    """)
    
    socketio.run(app, 
        host=host, 
        port=port, 
        debug=debug,
        use_reloader=False,  # 避免重复启动
        log_output=debug,
        allow_unsafe_werkzeug=True  # 允许生产环境运行
    )


def start_in_thread(host='0.0.0.0', port=8080):
    """在后台线程启动（供其他模块调用）"""
    thread = threading.Thread(
        target=start_server,
        args=(host, port, False),
        daemon=True
    )
    thread.start()
    return thread


# 直接运行
if __name__ == '__main__':
    start_server(debug=True)
