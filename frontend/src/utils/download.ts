/**
 * 浏览器文件下载工具：解析 Content-Disposition 中文文件名 + 触发下载
 * （导出 Excel / PDF 等 Blob 响应共用）
 */

/** 从 Content-Disposition 解析文件名（支持 filename*=UTF-8'' 中文） */
export function parseFilename(disposition: string | null): string | null {
  if (!disposition) return null;
  const star = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (star) {
    try {
      return decodeURIComponent(star[1]);
    } catch {
      /* fallthrough */
    }
  }
  const plain = disposition.match(/filename="?([^";]+)"?/i);
  return plain ? plain[1] : null;
}

/** 触发浏览器下载 Blob */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
