"""Step 02: 报错特征提取 — DOC-01 规则分类"""

import re
from error_governance.models.error_item import ErrorItem, ErrorFeatures


def extract(error_item: ErrorItem) -> ErrorFeatures:
    """按 DOC-01 决策树归类"""
    text = error_item.error_message

    # Step 1: 系统技术问题?
    if _match(text, ["Network Error", "timeout", "ECONNABORTED", "500", "502", "504"]):
        return _build("系统异常类", "网络/超时错误", "网络请求", "请求是否成功到达后端", "网络断开/超时/服务器错误")
    if _match(text, ["token", "session", "签名", "登录态", "登录已失效"]):
        return _build("权限类", "登录/会话失效", "任何需要登录态的操作", "校验有效性", "未登录/过期")
    if _match(text, ["远程服务", "接口调用异常", "RPC"]):
        return _build("系统异常类", "远程调用/接口异常", "调用外部接口", "调用是否成功", "超时/不可用")
    if _match(text, ["服务异常", "系统繁忙", "服务维护", "系统异常"]):
        return _build("系统异常类", "服务端通用异常", "后端操作", "服务是否正常", "服务异常/繁忙")

    # Step 2: 权限
    if _match(text, ["权限", "无访问", "管理员", "授权", "没有.*权限"]):
        if _match(text, ["数据权限", "部门", "账套", "区域", "数据范围"]):
            return _build("权限类", "数据权限不足", "查看/操作数据范围", "校验数据权限", "未授予权限")
        return _build("权限类", "操作权限不足", "执行功能操作", "校验操作权限码", "未分配权限")

    # Step 3: 数据校验
    if _match(text, ["不能为空", "必填"]):
        return _build("数据校验类", "参数为空校验", "表单提交", "必填校验", "必填字段未填写")
    if _match(text, ["格式不正确", "长度超过", "不合法", "格式错误"]):
        return _build("数据校验类", "参数格式/内容错误", "数据导入", "格式校验", "格式不符")
    if _match(text, ["已存在", "重复"]):
        return _build("数据校验类", "唯一性/重复校验", "新增数据", "唯一性校验", "与已有数据重复")
    if _match(text, ["文件", "上传", "导入", "解析失败", "模板"]):
        return _build("数据校验类", "文件上传校验", "文件上传", "文件校验", "格式/大小/内容")
    if _match(text, ["金额", "税额", "数值", "勾稽", "不等于", "不能为0"]):
        return _build("数据校验类", "金额/数值校验", "财务/薪资", "勾稽校验", "金额不一致/为0")

    # Step 4: 状态
    if _match(text, ["不存在", "已被删除", "未找到", "已删除"]):
        return _build("业务状态类", "数据/记录不存在", "查看数据", "存在性查询", "已删除/不存在")
    if _match(text, ["已处理", "请勿重复", "已结束"]):
        return _build("业务状态类", "重复操作/已处理", "审批/处理", "终态校验", "已被处理")
    if _match(text, ["锁定", "结账", "冻结", "不可修改"]):
        return _build("业务状态类", "已锁定/已冻结/已结账", "编辑数据", "锁定状态校验", "已锁定")
    if _match(text, ["流程中", "审批中", "处理中", "进行中"]):
        return _build("业务状态类", "流程中/处理中", "发起操作", "流程状态校验", "流程进行中")
    if _match(text, ["不允许", "不能", "不可进行操作"]):
        return _build("业务状态类", "状态不允许操作", "状态变更", "状态机校验", "状态不符")

    # Step 5: 业务领域
    if _match(text, ["考勤", "排班", "打卡", "请假", "调店"]):
        return _build("业务规则限制类", "考勤相关", "考勤操作", "考勤规则校验", "配置/冲突")
    if _match(text, ["薪资", "算税", "个税", "工资单", "薪酬"]):
        return _build("业务规则限制类", "薪资/算税相关", "薪资/个税", "状态校验", "锁定/算税中")
    if _match(text, ["发票", "税局", "税号", "开票"]):
        return _build("业务规则限制类", "发票/税务相关", "发票/税务", "发票/税局校验", "不匹配/失败")
    if _match(text, ["凭证", "账套", "科目", "借贷"]):
        return _build("业务规则限制类", "财务凭证相关", "凭证/账套", "凭证/结账校验", "重复/不存在")

    return _build("未分类", "未分类", "未知", "未知", "未知")


def _match(text: str, keywords: list[str]) -> bool:
    for kw in keywords:
        if re.search(kw, text, re.IGNORECASE):
            return True
    return False


MODULE_MAP = {
    "考勤": "考勤管理", "薪资": "薪资计算", "算税": "薪资计算",
    "财务": "财务管理", "凭证": "财务管理", "发票": "发票税务",
    "权限": "权限管理", "登录": "权限管理",
    "文件上传": "通用", "参数为空": "通用", "格式": "通用", "唯一性": "通用",
    "金额": "财务管理", "网络": "系统底层",
}


def _build(major: str, minor: str, task: str, validation: str, reason: str) -> ErrorFeatures:
    module = "通用业务"
    for k, v in MODULE_MAP.items():
        if k in minor:
            module = v
            break
    return ErrorFeatures(
        major_category=major, minor_category=minor, task_type=task,
        validation_logic=validation, error_reason=reason, business_module=module,
        search_keywords=[minor, reason] if reason != "未知" else [minor],
    )
