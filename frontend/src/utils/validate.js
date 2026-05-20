/**
 * 前端校验工具 —— 与后端 Pydantic 规则保持一致
 */

const USERNAME_RE = /^[a-zA-Z0-9_]{3,32}$/;
const PWD_MIN = 6;
const PWD_MAX = 128;

export function validateUsername(value) {
  if (!value || !value.trim()) return "用户名不能为空";
  if (!USERNAME_RE.test(value.trim())) return "格式：3-32位字母、数字、下划线";
  return null;
}

export function validatePassword(value) {
  if (!value) return "密码不能为空";
  if (value.length < PWD_MIN) return `密码至少 ${PWD_MIN} 位`;
  if (value.length > PWD_MAX) return `密码最多 ${PWD_MAX} 位`;
  return null;
}

export function validateConfirmPassword(password, confirm) {
  if (!confirm) return "请确认密码";
  if (password !== confirm) return "两次输入的密码不一致";
  return null;
}
