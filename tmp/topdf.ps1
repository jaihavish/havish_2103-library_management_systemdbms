param([string]$In, [string]$Out)
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$d = $w.Documents.Open($In, $false, $true)
$d.ExportAsFixedFormat($Out, 17)
$d.Close($false)
$w.Quit()
