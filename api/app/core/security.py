# 未来语法导入：支持前向引用的类型注解
from __future__ import annotations

# 导入Python标准库的安全相关模块
import base64  # Base64编解码，用于把二进制数据转成可存储的字符串
import hashlib  # 哈希算法库
import hmac  # 密钥相关的哈希消息认证码
import secrets  # 安全随机数生成器 - 专门用于密码学场景，不要用random模块！
from datetime import UTC, datetime, timedelta  # 时间处理相关

# 导入Argon2密码哈希库
# Argon2是目前密码哈希的行业标准，比bcrypt/scrypt更安全，是OWASP推荐算法
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# 导入AES-GCM加密算法 - 这是目前最安全最常用的对称加密算法
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# 导入配置获取函数
from app.core.config import get_settings

# 全局密码哈希器实例
# 开头的下划线是Python的约定，表示这是内部变量，不应该被外部模块直接导入使用
_password_hasher = PasswordHasher()


# 密码哈希函数：将明文密码转换成安全的哈希值
# 注意：这个哈希是单向的，无法从哈希值反推出原始密码
def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


# 密码验证函数：验证用户输入的密码是否和存储的哈希匹配
def verify_password(password: str, hashed_password: str) -> bool:
    try:
        # argon2的verify方法会自动处理盐值和算法参数
        return _password_hasher.verify(hashed_password, password)
    except VerifyMismatchError:
        # 密码不匹配时返回False，不要抛出异常
        return False


# 内部密钥派生函数：从用户提供的密码/密钥派生固定长度的加密密钥
# 开头的下划线表示这是模块内部函数，外部不应该直接调用
def _derive_key(secret: str) -> bytes:
    # 使用SHA-256哈希算法将任意长度的密钥转换成32字节的AES密钥
    return hashlib.sha256(secret.encode("utf-8")).digest()


# 加密函数：加密敏感数据（如用户的API密钥、令牌等）
# 加密后的数据可以安全存储在数据库中
def encrypt_secret(value: str) -> str:
    settings = get_settings()
    # 派生加密密钥
    key = _derive_key(settings.encryption_key)
    # 创建AES-GCM加密器实例
    aesgcm = AESGCM(key)
    # 生成12字节的随机nonce - AES-GCM标准推荐的长度
    # nonce不需要保密，但是每个加密操作必须使用唯一的nonce！
    nonce = secrets.token_bytes(12)
    # 执行加密：AES-GCM会同时加密数据并生成认证标签
    # 最后一个参数是附加认证数据，这里不需要
    ciphertext = aesgcm.encrypt(nonce, value.encode("utf-8"), None)
    # 将nonce和密文拼接在一起，然后用URL安全的Base64编码成字符串
    # nonce不需要保密，所以可以和密文存在一起
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")


# 解密函数：解密被encrypt_secret加密的数据
def decrypt_secret(value: str) -> str:
    settings = get_settings()
    # 派生和加密时完全相同的密钥
    key = _derive_key(settings.encryption_key)
    # 先把Base64字符串解码回原始的二进制数据
    raw = base64.urlsafe_b64decode(value.encode("utf-8"))
    # 拆分数据：前12字节是nonce，剩下的是密文+认证标签
    nonce, ciphertext = raw[:12], raw[12:]
    # 创建AES-GCM实例
    aesgcm = AESGCM(key)
    # 执行解密：AES-GCM会自动验证数据完整性
    # 如果数据被篡改，解密会直接抛出异常，不会返回错误的数据
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


# 生成会话令牌函数：创建一个安全的随机会话令牌
def generate_session_token() -> str:
    # 生成32字节(256位)的URL安全随机字符串
    # secrets模块使用操作系统提供的加密安全随机源
    return secrets.token_urlsafe(32)


# 会话令牌哈希函数：对会话令牌进行哈希后再存入数据库
# 这是重要的安全措施：即使数据库泄露，攻击者也无法用哈希后的令牌冒充用户
def hash_session_token(token: str) -> str:
    settings = get_settings()
    # 使用session_secret，如果没有设置则回退到encryption_key
    secret = settings.session_secret or settings.encryption_key
    # 使用HMAC-SHA256算法进行哈希
    # 这不是普通哈希，是带密钥的哈希，只有拥有密钥的人才能计算出相同的哈希值
    return hmac.new(
        secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256
    ).hexdigest()


# 获取会话过期时间函数：计算会话应该过期的时间点
def get_session_expiration() -> datetime:
    settings = get_settings()
    # 使用UTC时间！所有后端系统永远都应该用UTC时间存储和计算时间
    # 当前UTC时间加上配置的会话有效期小时数
    return datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)
