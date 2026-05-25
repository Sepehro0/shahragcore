# -*- coding: utf-8 -*-
"""Pydantic schemas for the Tool Registry API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolParameterProperty(BaseModel):
    type: str = "string"
    description: str = ""
    enum: Optional[List[str]] = None


class ToolParameters(BaseModel):
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class AuthConfig(BaseModel):
    type: str = Field("", description="bearer | api_key | basic | oauth2 | none")
    token: Optional[str] = None
    key: Optional[str] = None
    header_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    refresh_url: Optional[str] = Field(None, description="OAuth2 token refresh endpoint URL")
    refresh_token: Optional[str] = Field(None, description="OAuth2 refresh token")
    client_id: Optional[str] = Field(None, description="OAuth2 client ID")
    client_secret: Optional[str] = Field(None, description="OAuth2 client secret")
    token_expires_at: Optional[float] = Field(None, description="Unix timestamp when current token expires")


class RegisterToolRequest(BaseModel):
    name: str = Field(..., description="Unique function name, e.g. get_order_status")
    description: str = Field(..., description="What this tool does (Persian or English)")
    parameters: ToolParameters = Field(default_factory=ToolParameters)
    http_method: str = Field("GET", description="GET | POST | PUT | PATCH | DELETE")
    endpoint_url: str = Field(..., description="Full URL, may contain {param} placeholders")
    auth_config: AuthConfig = Field(default_factory=AuthConfig)
    trigger_description: str = Field(
        "",
        description="When should the model call this tool (Persian recommended)",
    )
    collection_name: str = Field(..., description="Which collection this tool belongs to")
    tenant_id: str = Field("", description="Optional tenant/user ID")
    headers: Dict[str, str] = Field(default_factory=dict)
    request_body_template: Optional[Dict[str, Any]] = None
    response_jmespath: Optional[str] = None
    timeout_seconds: int = Field(10, ge=1, le=60)
    # ── Auth-tool fields ──────────────────────────────────────────────────────
    is_auth_tool: bool = Field(
        False,
        description=(
            "اگر True باشد، این ابزار یک ابزار لاگین است. "
            "پس از اجرا، سیستم توکن را از پاسخ استخراج کرده و در SessionTokenStore ذخیره می‌کند. "
            "سپس سایر ابزارها می‌توانند با {{session.user_token}} از آن استفاده کنند."
        ),
    )
    token_path: str = Field(
        "",
        description=(
            "مسیر استخراج توکن از پاسخ API با نقطه‌گذاری. "
            "مثال: 'data.access_token' یا 'token' یا 'result.jwt'"
        ),
    )
    token_key: str = Field(
        "user_token",
        description=(
            "نام کلید ذخیره‌سازی توکن در SessionTokenStore. "
            "پیش‌فرض 'user_token'. سایر ابزارها با {{session.user_token}} به آن دسترسی دارند."
        ),
    )


class UpdateToolRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[ToolParameters] = None
    http_method: Optional[str] = None
    endpoint_url: Optional[str] = None
    auth_config: Optional[AuthConfig] = None
    trigger_description: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    request_body_template: Optional[Dict[str, Any]] = None
    response_jmespath: Optional[str] = None
    timeout_seconds: Optional[int] = None
    is_enabled: Optional[bool] = None
    is_auth_tool: Optional[bool] = None
    token_path: Optional[str] = None
    token_key: Optional[str] = None


class ToolResponse(BaseModel):
    tool_id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    http_method: str
    endpoint_url: str
    trigger_description: str
    collection_name: str
    is_enabled: bool
    timeout_seconds: int
    is_auth_tool: bool = False
    token_path: str = ""
    token_key: str = "user_token"


class ToolListResponse(BaseModel):
    collection_name: str
    tools: List[ToolResponse]
    count: int


class TestToolRequest(BaseModel):
    collection_name: str
    tool_name: str
    test_arguments: Dict[str, Any] = Field(default_factory=dict)


class TestToolResponse(BaseModel):
    success: bool
    status_code: Optional[int] = None
    data: Optional[Any] = None
    error: Optional[str] = None
    elapsed_ms: Optional[float] = None
