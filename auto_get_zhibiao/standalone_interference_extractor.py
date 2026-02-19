# -*- coding: utf-8 -*-
"""
独立干扰小区数据提取脚本
功能：单点登录大数据平台，进入即席查询模块，提取4G/5G干扰小区数据
特点：所有依赖模块已内嵌，可独立运行
"""
import requests
import os
import time
import json
import sys
import pandas as pd
from datetime import datetime, timedelta
from lxml import etree
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64
from urllib.parse import quote
import random
import pickle
import logging


# ==================== 配置区域 ====================
# 登录账号配置（请修改为你的账号）
DEFAULT_USERNAME = 'dwlianchangli'
DEFAULT_PASSWORD = 'Gmcc2026!@'

# 平台URL配置
BASE_URL = 'https://nqi.gmcc.net:20443'
LOGIN_URL = f'{BASE_URL}/cas/login?service={BASE_URL}/pro-portal/'
CAPTCHA_URL = f'{BASE_URL}/cas/captcha.jpg'
GET_CONFIG_URL = f'{BASE_URL}/cas/getConfig'
SEND_CODE_URL = f'{BASE_URL}/cas/sendCode1'
JXCX_URL = f'{BASE_URL}/pro-adhoc/adhocquery/getTable'
JXCX_COUNT_URL = f'{BASE_URL}/pro-adhoc/adhocquery/getTableCount'

# 输出目录配置
OUTPUT_DIR = './interference_data_output'
COOKIE_DIR = './cookies'
CAPTCHA_DIR = './captcha_images'
LOG_DIR = './logs'

# HTTP请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
}

HEADERS_JSON = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
    'Content-Type': 'application/json'
}


# ==================== 日志系统 ====================
# 全局日志记录器
_logger = None
_log_file_path = None

def setup_logging():
    """初始化日志系统"""
    global _logger, _log_file_path
    
    # 创建日志目录
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 生成日志文件名
    log_filename = datetime.now().strftime("standalone_log_%Y%m%d_%H%M%S.log")
    _log_file_path = os.path.join(LOG_DIR, log_filename)
    
    # 配置日志记录器
    _logger = logging.getLogger('InterferenceCellExtractor')
    _logger.setLevel(logging.DEBUG)
    
    # 清除已有的处理器
    _logger.handlers.clear()
    
    # 文件处理器
    file_handler = logging.FileHandler(_log_file_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 日志格式
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
    console_formatter = logging.Formatter('%(message)s')
    
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    _logger.addHandler(file_handler)
    _logger.addHandler(console_handler)
    
    # 记录启动信息
    _logger.info("=" * 60)
    _logger.info("干扰小区数据提取工具 (独立命令行版) 启动")
    _logger.info(f"日志文件: {_log_file_path}")
    _logger.info("=" * 60)
    
    return _logger, _log_file_path

def log_print(message, level='INFO'):
    """打印并记录日志"""
    if _logger:
        if level == 'ERROR':
            _logger.error(message)
        elif level == 'WARNING':
            _logger.warning(message)
        elif level == 'DEBUG':
            _logger.debug(message)
        else:
            _logger.info(message)
    else:
        print(message)

# 重写print函数
_original_print = print
def print(*args, **kwargs):
    """重写的print函数，同时输出到控制台和日志文件"""
    message = ' '.join(map(str, args))
    
    # 判断日志级别
    if '✗' in message or '失败' in message or '错误' in message:
        level = 'ERROR'
    elif '⚠' in message or '警告' in message:
        level = 'WARNING'
    else:
        level = 'INFO'
    
    log_print(message, level)


# ==================== 工具函数 ====================
def ensure_dirs():
    """确保必要的目录存在"""
    for dir_path in [OUTPUT_DIR, COOKIE_DIR, CAPTCHA_DIR, LOG_DIR]:
        os.makedirs(dir_path, exist_ok=True)


def save_cookie(cookie, username):
    """保存cookie到文件"""
    ensure_dirs()
    filepath = os.path.join(COOKIE_DIR, f'{username}.pkl')
    with open(filepath, 'wb') as f:
        pickle.dump(cookie, f)


def load_cookie(username):
    """从文件加载cookie"""
    filepath = os.path.join(COOKIE_DIR, f'{username}.pkl')
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    return None


def rsa_encrypt(data, public_key):
    """RSA加密"""
    public_key = '-----BEGIN PUBLIC KEY-----\n' + public_key + '\n-----END PUBLIC KEY-----'
    rsa_key = RSA.importKey(public_key)
    cipher = PKCS1_v1_5.new(rsa_key)
    encrypted_data = base64.b64encode(cipher.encrypt(data.encode(encoding="utf-8")))
    return encrypted_data.decode('utf-8')


def captcha_handle(img_content, attempt=1):
    """验证码处理（OCR识别）"""
    try:
        from PIL import Image, ImageFilter
        import pytesseract
        from io import BytesIO
        
        bytes_stream = BytesIO(img_content)
        img = Image.open(bytes_stream)
        img_gray = img.convert('L')
        img_black_white = img_gray.point(lambda x: 255 if x > 85 else 0)
        img_qucao = img_black_white.filter(ImageFilter.SMOOTH_MORE)
        img = img_qucao.convert('RGB')
        
        config = '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        result = pytesseract.image_to_string(img, config=config)[0:4].replace('\n', '')
        return result
    except Exception as e:
        print(f"验证码OCR识别失败: {e}")
        # 保存验证码图片供手动输入
        ensure_dirs()
        img_path = os.path.join(CAPTCHA_DIR, f'captcha_{attempt}.jpg')
        with open(img_path, 'wb') as f:
            f.write(img_content)
        return None


# ==================== 登录模块 ====================
class LoginManager:
    """登录管理器"""
    
    def __init__(self, username=None, password=None):
        self.username = username or DEFAULT_USERNAME
        self.password = password or DEFAULT_PASSWORD
        self.sess = requests.Session()
    
    def login(self, try_times=3):
        """执行登录"""
        print("=" * 60)
        print("开始登录大数据平台...")
        print(f"账号: {self.username}")
        print("=" * 60)
        
        # 1. 尝试使用保存的cookie
        saved_cookie = load_cookie(self.username)
        if saved_cookie:
            self.sess.cookies = saved_cookie
            if self._check_session():
                print("✓ 使用保存的Cookie登录成功！")
                return True
            else:
                print("⚠ 保存的Cookie已失效，重新登录...")
                self.sess = requests.Session()
        
        # 2. 执行完整登录流程
        for i in range(try_times):
            if self._login_once(i):
                print(f"✓ 登录成功！（尝试次数: {i+1}）")
                save_cookie(self.sess.cookies, self.username)
                return True
            else:
                print(f"⚠ 登录失败，尝试次数: {i+1}/{try_times}")
        
        print("✗ 登录失败，已达到最大尝试次数")
        return False
    
    def _check_session(self):
        """检查session是否有效"""
        try:
            url = f'{BASE_URL}/pro-wfm-biz-server/cas/login/info'
            res = self.sess.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                data = json.loads(res.text)
                return data.get('data', {}).get('loginId') == self.username
        except:
            pass
        return False

    
    def _login_once(self, attempt=0):
        """执行一次完整的登录流程"""
        try:
            # 获取公钥和execution
            res = self.sess.get(LOGIN_URL, headers=HEADERS)
            res.encoding = 'utf-8'
            html = etree.HTML(res.text)
            
            execution = html.xpath('//*[@id="fm1"]/div[4]/input[1]')[0].attrib.get('value')
            public_key = html.xpath('//*[@type="text/javascript"]/text()')[0].split('setPublicKey("')[1].split('")')[0]
            
            # 加密用户名和密码
            username_e = rsa_encrypt(self.username, public_key)
            password_e = rsa_encrypt(self.password, public_key)
            
            # 图形验证码验证
            captcha_code = None
            for i in range(10):
                captcha_res = self.sess.get(CAPTCHA_URL)
                
                if i < 5:  # 前5次尝试OCR
                    captcha_code = captcha_handle(captcha_res.content, attempt * 10 + i)
                
                if not captcha_code:  # OCR失败或超过5次，手动输入
                    ensure_dirs()
                    img_path = os.path.join(CAPTCHA_DIR, f'captcha_{attempt}_{i}.jpg')
                    with open(img_path, 'wb') as f:
                        f.write(captcha_res.content)
                    captcha_code = input(f'请查看图片 {img_path} 并输入验证码: ')
                
                # 验证图形验证码
                data = {
                    'password': password_e,
                    'loginId': username_e,
                    'captcha': captcha_code,
                }
                res = self.sess.post(GET_CONFIG_URL, data=json.dumps(data), headers=HEADERS_JSON)
                
                if res.status_code == 200:
                    result = json.loads(res.text)
                    if result.get('code') == '1':
                        print(f"✓ 图形验证码验证通过（尝试次数: {i+1}）")
                        break
                    else:
                        print(f"⚠ 图形验证码错误，重试...")
                        captcha_code = None
            else:
                print("✗ 图形验证码验证失败次数过多")
                return False

            
            # 发送短信验证码（仅第一次）
            if attempt == 0:
                data_sms = {'loginId': username_e, 'password': password_e}
                res_sms = self.sess.post(SEND_CODE_URL, data=json.dumps(data_sms), headers=HEADERS_JSON)
                result_sms = json.loads(res_sms.text)
                if result_sms.get('msg') == 'success':
                    print("✓ 短信验证码已发送")
                else:
                    print("⚠ 短信验证码发送失败")
            
            # 输入短信验证码
            msg_code = input('请输入短信验证码: ')
            
            # 提交登录
            login_data = {
                'password': password_e,
                'username': username_e,
                'msgCode': msg_code,
                'captcha': captcha_code,
                'uuid': '',
                'execution': execution,
                '_eventId': 'submit',
                'geolocation': ''
            }
            
            res_login = self.sess.post(LOGIN_URL, data=login_data, headers=HEADERS)
            
            # 检查是否登录成功
            if self.sess.cookies.get('CASTGC'):
                return True
            else:
                print("⚠ 短信验证码错误")
                return False
                
        except Exception as e:
            print(f"✗ 登录过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False


# ==================== 即席查询模块 ====================
class JXCXQuery:
    """即席查询类"""
    
    def __init__(self, session):
        self.sess = session
        self.enabled = False
    
    def enter_jxcx(self, retry_times=3, timeout=60):
        """进入即席查询模块"""
        print("\n进入即席查询模块...")
        
        for attempt in range(retry_times):
            if attempt > 0:
                print(f"\n  重试第 {attempt} 次...")
                time.sleep(2)  # 重试前等待2秒
            
            try:
                # 1. 获取CASTGC cookie
                print("  [1/4] 获取CASTGC cookie...")
                castgc = self.sess.cookies.get('CASTGC', domain='nqi.gmcc.net')
                if not castgc:
                    castgc = self.sess.cookies.get('CASTGC')
                
                if not castgc:
                    print("  ✗ 未找到CASTGC cookie")
                    print(f"  当前cookies: {list(self.sess.cookies.keys())}")
                    continue
                
                print(f"  ✓ CASTGC获取成功: {castgc[:20]}...")
                
                # 2. 构建请求URL
                print("  [2/4] 构建请求URL...")
                url = f'{BASE_URL}/pro-portal/pure/urlAction.action'
                params = {
                    'url': 'pro-adhoc/index',
                    'random': random.random(),
                    '__PID': 'JXCX',
                    'token': castgc
                }
                
                url_with_params = f"{url}?url={params['url']}&__PID={params['__PID']}&random={params['random']}&token={params['token']}"
                print(f"  ✓ URL构建完成")
                print(f"  请求地址: {url}")
                
                # 3. 发送请求
                print(f"  [3/4] 发送请求到即席查询模块（超时设置: {timeout}秒）...")
                start_time = time.time()
                res = self.sess.get(url_with_params, headers=HEADERS, timeout=timeout)
                elapsed_time = time.time() - start_time
                print(f"  ✓ 请求完成，耗时: {elapsed_time:.2f}秒，状态码: {res.status_code}")
                print(f"  响应大小: {len(res.content)} bytes")
                
                # 4. 检查响应
                print("  [4/4] 检查响应结果...")
                if res.status_code == 200:
                    # 检查响应内容
                    if len(res.content) > 0:
                        print(f"  ✓ 响应内容正常")
                        # 尝试检查是否包含即席查询相关内容
                        if 'adhoc' in res.text.lower() or 'jxcx' in res.text.lower():
                            print("  ✓ 响应包含即席查询相关内容")
                        else:
                            print("  ⚠ 响应中未找到即席查询关键字，但继续尝试")
                    else:
                        print("  ⚠ 响应内容为空")
                    
                    self.enabled = True
                    print("✓ 即席查询模块初始化成功！")
                    return True
                else:
                    print(f"✗ 进入即席查询失败，状态码: {res.status_code}")
                    print(f"  响应内容: {res.text[:500]}")
                    continue
                    
            except requests.exceptions.Timeout:
                print(f"  ✗ 进入即席查询超时（{timeout}秒）")
                if attempt < retry_times - 1:
                    print(f"  将在2秒后重试...")
                continue
            except requests.exceptions.ConnectionError as e:
                print(f"  ✗ 网络连接错误: {e}")
                if attempt < retry_times - 1:
                    print(f"  将在2秒后重试...")
                continue
            except requests.exceptions.RequestException as e:
                print(f"  ✗ 请求错误: {e}")
                if attempt < retry_times - 1:
                    print(f"  将在2秒后重试...")
                continue
            except Exception as e:
                print(f"  ✗ 未知错误: {e}")
                import traceback
                print(f"  错误详情: {traceback.format_exc()}")
                continue
        
        print(f"✗ 进入即席查询失败，已尝试 {retry_times} 次")
        return False
    
    def get_table_count(self, payload):
        """获取查询结果行数"""
        if not self.enabled:
            print("  即席查询未启用，尝试重新进入...")
            self.enter_jxcx()
        
        print("  正在获取数据总行数...")
        key_list = ['geographicdimension', 'timedimension', 'enodebField', 'cgiField',
                    'timeField', 'cellField', 'cityField', 'result', 'where', 'indexcount']
        payload_count = {key: value for key, value in payload.items() if key in key_list}
        payload_encoded = self._encode_payload(payload_count)
        
        try:
            res = self.sess.post(JXCX_COUNT_URL, data=payload_encoded, headers=HEADERS, timeout=30)
            if res.status_code == 200:
                result = json.loads(res.content)
                count = result.get('count', 1000000)
                print(f"  ✓ 数据总行数: {count}")
                return count
            else:
                print(f"  ⚠ 获取行数失败，状态码: {res.status_code}，使用默认值")
                return 1000000
        except Exception as e:
            print(f"  ⚠ 获取行数出错: {e}，使用默认值")
            return 1000000

    
    def get_table(self, payload, to_df=True):
        """获取查询数据"""
        if not self.enabled:
            print("  即席查询未启用，尝试重新进入...")
            self.enter_jxcx()
        
        print("\n开始查询数据...")
        
        # 1. 获取数据总行数
        if 'length' in payload:
            print("  [1/3] 获取数据总行数...")
            payload['length'] = self.get_table_count(payload)
        
        # 2. 编码payload
        print("  [2/3] 编码查询参数...")
        payload_encoded = self._encode_payload(payload)
        print(f"  ✓ 参数编码完成，长度: {len(payload_encoded)} bytes")
        
        # 3. 发送查询请求
        print("  [3/3] 发送查询请求...")
        try:
            res = self.sess.post(JXCX_URL, data=payload_encoded, headers=HEADERS, timeout=60)
            print(f"  ✓ 查询请求完成，状态码: {res.status_code}")
            print(f"  响应大小: {len(res.content)} bytes")
        except requests.exceptions.Timeout:
            print(f"  ✗ 查询请求超时（60秒）")
            return pd.DataFrame() if to_df else {}
        except Exception as e:
            print(f"  ✗ 查询请求失败: {e}")
            return pd.DataFrame() if to_df else {}
        
        if res.status_code != 200:
            print(f"✗ 查询失败，状态码: {res.status_code}")
            print(f"  响应内容: {res.text[:500]}")
            return pd.DataFrame() if to_df else {}
        
        # 4. 解析响应
        print("  解析响应数据...")
        try:
            result = json.loads(res.content)
            
            if 'data' not in result:
                print(f"  ✗ 响应中没有data字段")
                print(f"  响应内容: {str(result)[:500]}")
                return pd.DataFrame() if to_df else {}
            
            data_count = len(result.get('data', []))
            print(f"  ✓ 解析成功，获取到 {data_count} 条数据")
            
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON解析失败: {e}")
            print(f"  响应内容: {res.text[:500]}")
            return pd.DataFrame() if to_df else {}
        
        if to_df:
            # 转换为DataFrame
            print("  转换为DataFrame格式...")
            try:
                en_zh_df = self._get_field_mapping(payload)
                res_df = pd.DataFrame(result['data'])
                
                if res_df.empty:
                    print("  ⚠ 查询结果为空")
                    return pd.DataFrame()
                
                res_df = pd.concat([en_zh_df, res_df], ignore_index=True)
                
                # 使用第一行作为列名
                index_first = res_df.index.tolist()[0]
                to_colname = list(res_df.loc[index_first])
                res_df.columns = to_colname
                res_df.drop(index=index_first, inplace=True)
                
                print(f"  ✓ DataFrame转换完成，形状: {res_df.shape}")
                return res_df
            except Exception as e:
                print(f"  ✗ DataFrame转换失败: {e}")
                import traceback
                print(f"  错误详情: {traceback.format_exc()}")
                return pd.DataFrame()
        else:
            return result
    
    def _encode_payload(self, payload):
        """编码payload为URL格式"""
        out_list = []
        for key in payload:
            if key not in ['result', 'where']:
                right = str(payload[key]) if type(payload[key]) is int else quote(str(payload[key]))
            else:
                right = quote(json.dumps(payload[key]))
            out_list.append(quote(key) + '=' + right)
        return '&'.join(out_list)
    
    def _get_field_mapping(self, payload):
        """获取字段中英文映射"""
        result_list = payload['result']['result']
        result_df = pd.DataFrame(result_list)
        zn = list(result_df['feildName'])
        en = list(result_df['feild'])
        en_zh_dict = dict(zip(en, zn))
        return pd.DataFrame([en_zh_dict])


# ==================== Payload模板 ====================
def get_5g_interference_payload():
    """获取5G干扰小区查询payload"""
    return {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区', 'timedimension': '天',
        'enodebField': 'gnodeb_id', 'cgiField': 'cgi', 'timeField': 'starttime',
        'cellField': 'cell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '数据时间', 'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '结束时间', 'feild': 'endtime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': 'CGI', 'feild': 'cgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '小区名', 'feild': 'cell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '频段', 'feild': 'freq', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '微网格标识', 'feild': 'micro_grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '全频段均值', 'feild': 'averagevalue', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': 'D1均值', 'feild': 'averagevalued1', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': 'D2均值', 'feild': 'averagevalued2', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '是否干扰小区', 'feild': 'is_interfere_5g', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'}
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=',
             'val': '2025-01-13 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<',
             'val': '2025-01-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in',
             'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }



def get_4g_interference_payload():
    """获取4G干扰小区查询payload"""
    return {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区', 'timedimension': '天',
        'enodebField': 'enodeb_id', 'cgiField': 'cgi', 'timeField': 'starttime',
        'cellField': 'cell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': '1', 'feildName': '数据时间',
             'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': '1', 'feildName': '结束时间',
             'feild': 'endtime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': '1', 'feildName': 'CGI',
             'feild': 'cgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '小区名', 'feild': 'cell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '频段', 'feild': 'freq', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '微网格标识', 'feild': 'micro_grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '系统带宽', 'feild': 'bandwidth', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '平均干扰电平', 'feild': 'averagevalue', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '是否干扰小区', 'feild': 'is_interfere', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'}
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=',
             'val': '2025-01-13 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<',
             'val': '2025-01-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in',
             'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }


def set_payload_time(payload, start_time, end_time):
    """设置payload的查询时间"""
    for condition in payload['where']:
        if condition['feild'] in ['day_id', 'starttime']:
            if condition['symbol'] in ['>=', '>']:
                condition['val'] = start_time
            elif condition['symbol'] in ['<', '<=']:
                condition['val'] = end_time
    return payload


def set_payload_city(payload, city):
    """设置payload的查询城市"""
    for condition in payload['where']:
        if condition['feild'] == 'city':
            condition['val'] = city
    return payload


# ==================== 干扰小区提取器 ====================
class InterferenceCellExtractor:
    """干扰小区数据提取器"""
    
    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.login_mgr = None
        self.jxcx = None
    
    def login(self):
        """执行登录"""
        self.login_mgr = LoginManager(self.username, self.password)
        return self.login_mgr.login()
    
    def init_jxcx(self):
        """初始化即席查询"""
        if not self.login_mgr:
            print("✗ 请先执行登录")
            return False
        
        self.jxcx = JXCXQuery(self.login_mgr.sess)
        # 使用更长的超时时间和重试机制
        return self.jxcx.enter_jxcx(retry_times=3, timeout=60)
    
    def extract_data(self, network_type='5G', start_date=None, end_date=None,
                    city='阳江', only_interfered=True):
        """
        提取干扰小区数据
        :param network_type: '4G' 或 '5G'
        :param start_date: 开始日期 '2025-01-13' 或 datetime对象
        :param end_date: 结束日期 '2025-01-19' 或 datetime对象
        :param city: 城市名称
        :param only_interfered: 是否只提取干扰小区
        :return: DataFrame
        """
        print("\n" + "=" * 60)
        print(f"开始提取 {network_type} 干扰小区数据")
        print("=" * 60)
        
        # 处理日期
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now() - timedelta(days=1)
        
        if isinstance(start_date, str):
            start_time = start_date + ' 00:00:00'
        else:
            start_time = start_date.strftime('%Y-%m-%d 00:00:00')
        
        if isinstance(end_date, str):
            end_time = end_date + ' 23:59:59'
        else:
            end_time = end_date.strftime('%Y-%m-%d 23:59:59')
        
        print(f"查询参数:")
        print(f"  网络类型: {network_type}")
        print(f"  开始时间: {start_time}")
        print(f"  结束时间: {end_time}")
        print(f"  城市: {city}")
        print(f"  仅干扰小区: {only_interfered}")
        
        try:
            # 获取payload
            if network_type == '5G':
                payload = get_5g_interference_payload()
                interfere_field = '是否干扰小区'
            elif network_type == '4G':
                payload = get_4g_interference_payload()
                interfere_field = '是否干扰小区'
            else:
                raise ValueError("network_type 必须是 '4G' 或 '5G'")
            
            # 设置查询条件
            payload = set_payload_time(payload, start_time, end_time)
            payload = set_payload_city(payload, city)
            
            # 查询数据
            print("\n正在查询数据...")
            df = self.jxcx.get_table(payload, to_df=True)
            print(f"✓ 查询成功，共 {len(df)} 条记录")
            
            # 过滤干扰小区
            if only_interfered and interfere_field in df.columns:
                original_count = len(df)
                df = df[df[interfere_field] == '是']
                print(f"✓ 过滤后保留干扰小区 {len(df)} 个（原始 {original_count} 条）")
            
            return df
            
        except Exception as e:
            print(f"✗ 数据提取失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def save_to_excel(self, df, filename=None, network_type='5G'):
        """保存数据到Excel"""
        if df.empty:
            print("\n⚠ 数据为空，不保存文件")
            return
        
        ensure_dirs()
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{network_type}_干扰小区_{timestamp}.xlsx'
        
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        try:
            df.to_excel(filepath, index=False, engine='openpyxl')
            print(f"\n✓ 数据已保存: {filepath}")
            print(f"  文件大小: {os.path.getsize(filepath) / 1024:.2f} KB")
            return filepath
        except Exception as e:
            print(f"\n✗ 保存文件失败: {e}")
            return None


# ==================== 主函数 ====================
def main():
    """主函数 - 交互式提取"""
    # 初始化日志系统
    logger, log_file = setup_logging()
    
    print("\n" + "=" * 60)
    print("干扰小区数据提取工具 (独立版)")
    print("=" * 60)
    print(f"日志文件: {log_file}")
    print("=" * 60)
    
    # 选择网络类型
    print("\n请选择网络类型:")
    print("1. 5G")
    print("2. 4G")
    print("3. 同时提取4G和5G")
    choice = input("请输入选项 (1/2/3，默认1): ").strip() or '1'
    
    if choice == '3':
        network_types = ['5G', '4G']
    elif choice == '2':
        network_types = ['4G']
    else:
        network_types = ['5G']
    
    # 输入查询天数
    days_input = input("\n查询最近几天的数据 (默认7天): ").strip()
    days = int(days_input) if days_input else 7
    
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=days-1)
    
    # 输入城市
    city = input("\n请输入城市名称 (默认'阳江'): ").strip() or '阳江'
    
    # 是否只提取干扰小区
    only_interfered_input = input("\n是否只提取干扰小区? (y/n，默认y): ").strip().lower()
    only_interfered = only_interfered_input != 'n'
    
    # 创建提取器
    extractor = InterferenceCellExtractor()
    
    # 登录
    if not extractor.login():
        print("\n✗ 登录失败，程序退出")
        return
    
    # 初始化即席查询
    if not extractor.init_jxcx():
        print("\n✗ 初始化即席查询失败，程序退出")
        return
    
    # 提取数据
    for network_type in network_types:
        df = extractor.extract_data(
            network_type=network_type,
            start_date=start_date,
            end_date=end_date,
            city=city,
            only_interfered=only_interfered
        )
        
        if not df.empty:
            # 保存数据
            filepath = extractor.save_to_excel(df, network_type=network_type)
            
            # 显示统计
            print(f"\n{network_type} 数据统计:")
            print(f"  总记录数: {len(df)}")
            print(f"\n前5条数据预览:")
            print(df.head().to_string())
    
    print("\n" + "=" * 60)
    print("数据提取完成！")
    print(f"输出目录: {os.path.abspath(OUTPUT_DIR)}")
    print(f"日志文件: {_log_file_path}")
    print("=" * 60)
    
    # 记录结束信息
    if _logger:
        _logger.info("=" * 60)
        _logger.info("干扰小区数据提取工具 (独立命令行版) 结束")
        _logger.info("=" * 60)


def quick_extract(network_type='5G', days=7, city='阳江', username=None, password=None):
    """
    快速提取函数 - 供脚本调用
    
    使用示例:
        quick_extract(network_type='5G', days=7, city='阳江')
    """
    # 初始化日志系统
    if _logger is None:
        setup_logging()
    
    extractor = InterferenceCellExtractor(username, password)
    
    if not extractor.login():
        return None
    
    if not extractor.init_jxcx():
        return None
    
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=days-1)
    
    df = extractor.extract_data(
        network_type=network_type,
        start_date=start_date,
        end_date=end_date,
        city=city,
        only_interfered=True
    )
    
    if not df.empty:
        filepath = extractor.save_to_excel(df, network_type=network_type)
        return df, filepath
    
    return None, None


if __name__ == '__main__':
    # 交互式运行
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        if _logger:
            _logger.info("用户取消操作")
    except Exception as e:
        print(f"\n✗ 程序执行失败: {e}")
        if _logger:
            _logger.error(f"程序执行失败: {e}")
        import traceback
        traceback.print_exc()
        if _logger:
            _logger.error(traceback.format_exc())
