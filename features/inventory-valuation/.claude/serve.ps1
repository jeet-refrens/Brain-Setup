param([int]$Port = 5500)
$root = Split-Path -Parent $PSScriptRoot
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Start()
Write-Host "Serving $root on http://localhost:$Port/"
while ($listener.IsListening) {
    try {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response
        try {
            $path = $request.Url.LocalPath
            if ($path -eq "/") { $path = "/inventory-valuation-flow-explorer.html" }
            $filePath = Join-Path $root $path.TrimStart("/")
            if (Test-Path $filePath -PathType Leaf) {
                $bytes = [System.IO.File]::ReadAllBytes($filePath)
                $ext = [System.IO.Path]::GetExtension($filePath)
                $contentType = switch ($ext) {
                    ".html" { "text/html; charset=utf-8" }
                    ".js"   { "application/javascript" }
                    ".css"  { "text/css" }
                    default { "application/octet-stream" }
                }
                $response.ContentType = $contentType
                $response.ContentLength64 = $bytes.LongLength
                $response.OutputStream.Write($bytes, 0, $bytes.Length)
            } else {
                $response.StatusCode = 404
            }
        } catch {
            Write-Host "Request error: $_"
        } finally {
            $response.OutputStream.Close()
        }
    } catch {
        Write-Host "Listener error: $_"
    }
}
