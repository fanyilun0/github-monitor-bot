import asyncio
import aiohttp
from datetime import datetime, timedelta
import logging

# 导入配置
from config import (
    GITHUB_API,  # GitHub API
    WEBHOOK_URL, 
    PROXY_URL, 
    USE_PROXY, 
    INTERVAL, 
    TIME_OFFSET,
    APP_NAME,
    REPOS_CONFIG
)

# 配置logging
def setup_logging():
    """配置日志格式和级别"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

async def fetch_commits(session, owner, repo):
    """获取仓库最新提交"""
    api_url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"
    headers = {
        "accept": "application/json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        async with session.get(api_url, headers=headers, ssl=False) as response:
            if response.status == 200:
                commits = await response.json()
                if commits:
                    latest_commit = commits[0]  # 获取最新的提交
                    
                    # 获取详细的commit信息
                    commit_url = f"{GITHUB_API}/repos/{owner}/{repo}/commits/{latest_commit['sha']}"
                    async with session.get(commit_url, headers=headers, ssl=False) as detail_response:
                        if detail_response.status == 200:
                            commit_detail = await detail_response.json()
                            changed_files = [file['filename'] for file in commit_detail['files']]
                            
                            return {
                                'sha': latest_commit['sha'],
                                'message': latest_commit['commit']['message'],
                                'author': latest_commit['commit']['author']['name'],
                                'date': latest_commit['commit']['author']['date'],
                                'url': latest_commit['html_url'],
                                'files': changed_files  # 添加变更文件列表
                            }
            logger.error(f"获取提交失败: {response.status}")
            return None
    except Exception as e:
        logger.error(f"获取提交出错: {str(e)}")
        return None

def build_message(repo_commits):
    """构建包含所有新提交的通知消息"""
    adjusted_time = datetime.now() + timedelta(hours=TIME_OFFSET)
    timestamp = adjusted_time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 计算下一次检查时间
    next_check = adjusted_time + timedelta(seconds=INTERVAL)
    next_check_str = next_check.strftime('%Y-%m-%d %H:%M:%S')
    
    message = (
        f"🔍 【{APP_NAME} 状态报告】\n"
        f"⏰ 当前时间: {timestamp}\n"
        f"⏭ 下次检查: {next_check_str}\n\n"
    )
    
    for repo_name, commit in repo_commits.items():
        message += (
            f"📦 仓库: {repo_name}\n"
            f"👤 作者: {commit['author']}\n"
            f"📝 消息: {commit['message']}\n"
            f"🔗 链接: {commit['url']}\n"
            f"⌚️ 提交时间: {commit['date']}\n\n"
        )
    
    return message.strip()

async def send_message_async(webhook_url, message_content, use_proxy, proxy_url):
    """发送消息到webhook"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "msgtype": "text",
        "text": {
            "content": message_content
        }
    }
    
    proxy = proxy_url if use_proxy else None
    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload, headers=headers, proxy=proxy) as response:
            if response.status == 200:
                logger.info("消息发送成功!")
            else:
                logger.error(f"发送消息失败: {response.status}")

async def monitor_single_repo(session, repo_config, previous_commits):
    """监控单个仓库的提交"""
    try:
        logger.info(f"开始检查仓库: {repo_config['name']}")
        
        commit = await fetch_commits(session, repo_config['owner'], repo_config['repo'])
        if commit is None:
            return None
            
        # 检查是否有新提交
        previous_sha = previous_commits.get(repo_config['name'])
        if previous_sha != commit['sha']:
            logger.info(f"发现新提交: {commit['sha']}")
            return repo_config['name'], commit
            
        logger.info("没有新提交")
        return None
        
    except Exception as e:
        logger.error(f"❌ 监控仓库 {repo_config['name']} 时出错: {str(e)}")
        return None
    finally:
        logger.info(f"检查完成: {repo_config['name']}")

async def monitor_repos(interval, webhook_url, use_proxy, proxy_url):
    """主监控函数"""
    iteration = 1
    previous_commits = {}  # 存储上次检查的commit SHA

    while True:
        try:
            logger.info(f"\n开始第 {iteration} 轮检查...")
            new_commits = {}
            
            # 解析仓库配置并输出正在监听的仓库  
            for repo_config in REPOS_CONFIG:
                logger.info(f"正在监听仓库📦 : {repo_config['name']}")

            async with aiohttp.ClientSession() as session:
                for repo_config in REPOS_CONFIG:
                    result = await monitor_single_repo(session, repo_config, previous_commits)
                    if result:
                        repo_name, commit = result
                        new_commits[repo_name] = commit
                        # 更新上次检查的commit SHA
                        previous_commits[repo_name] = commit['sha']
            
            if new_commits:  # 有新提交时才发送消息
                message = build_message(new_commits)
                await send_message_async(webhook_url, message, use_proxy, proxy_url)
                logger.info("✅ 消息发送成功")
            
            logger.info(f"第 {iteration} 轮检查完成\n")
            iteration += 1
            
        except Exception as e:
            logger.error(f"监控过程出错: {str(e)}")
            await asyncio.sleep(5)  # 保留错误后的短暂延迟
            continue
            
        await asyncio.sleep(interval)

if __name__ == "__main__":
    asyncio.run(monitor_repos(
        interval=INTERVAL,
        webhook_url=WEBHOOK_URL,
        use_proxy=USE_PROXY,
        proxy_url=PROXY_URL
    ))
