# 未来语法导入：支持前向引用的类型注解
from __future__ import annotations

# 导入SQLAlchemy的声明式基类
# DeclarativeBase是SQLAlchemy 2.0的新API，替代了旧版的declarative_base()函数
from sqlalchemy.orm import DeclarativeBase


# 数据库模型基类
# 这个类是整个项目所有数据库模型的父类，所有的表模型都要继承这个Base类
#
# 虽然看起来这个类什么代码都没有，只有一个pass，但它是SQLAlchemy ORM的核心：
# 1. 所有继承Base的类都会被SQLAlchemy自动识别为数据库表模型
# 2. SQLAlchemy会通过这个类来管理所有表的元数据
# 3. 迁移工具(Alembic)会通过这个类来自动检测表结构变化
# 4. 你可以在这里给所有模型添加通用的字段和方法(如创建时间、更新时间等)
#
# 这是SQLAlchemy项目的标准写法，每个项目都有一个这样的base.py文件
class Base(DeclarativeBase):
    pass
