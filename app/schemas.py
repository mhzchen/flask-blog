"""Pydantic v2 请求体模型 + 通用校验装饰器。

设计要点：
- 用 Pydantic 统一声明请求体结构、字段约束（必填/长度/类型），并自动完成解析与校验；
- 校验失败统一返回 422 + 字段级错误，前端能据此定位具体字段；
- 校验通过后，把解析好的 Pydantic 实例放到 g.validated 供视图使用。
"""
from functools import wraps

from flask import request, jsonify, g
from pydantic import BaseModel, Field, EmailStr, ValidationError


# ---------- 请求体模型 ----------

class RegisterBody(BaseModel):
    """注册请求体"""
    username: str = Field(..., min_length=1, max_length=30, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=128, description="密码，至少 6 位")


class LoginBody(BaseModel):
    """登录请求体"""
    username: str = Field(..., min_length=1, max_length=30, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


class PostBody(BaseModel):
    """创建/更新文章请求体"""
    title: str = Field(..., min_length=1, max_length=200, description="文章标题")
    summary: str = Field("", max_length=500, description="摘要")
    content: str = Field("", description="正文")
    category_id: int = Field(..., gt=0, description="所属分类 ID")


class CategoryBody(BaseModel):
    """创建/更新分类请求体"""
    name: str = Field(..., min_length=1, max_length=50, description="分类名")
    slug: str = Field("", max_length=50, description="唯一标识，留空自动生成")


# ---------- 校验装饰器 ----------

def validate_body(model: type[BaseModel]):
    """校验请求 JSON 体。

    失败：返回 422 + {'error', 'fields': {字段: 错误信息}}。
    成功：把 Pydantic 实例写入 g.validated，然后执行视图函数。
    """
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            data = request.get_json(silent=True) or {}
            try:
                g.validated = model.model_validate(data)
            except ValidationError as e:
                errors = {}
                for err in e.errors():
                    # loc 形如 ('body', 'username') 或 ('username',)；取最后一段作为字段名
                    field = err['loc'][-1] if err['loc'] else 'body'
                    errors[str(field)] = err['msg']
                return jsonify({'error': '请求参数校验失败', 'fields': errors}), 422
            return fn(*args, **kwargs)
        return wrapper
    return deco