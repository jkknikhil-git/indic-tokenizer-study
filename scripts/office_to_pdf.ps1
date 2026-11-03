# Convert the report (.docx) and slides (.pptx) to PDF with Microsoft Office, updating Word fields
# (table of contents, list of figures/tables) first.
# Usage: powershell -File scripts/office_to_pdf.ps1 [-What docx|pptx|all] [-Docx report\report.docx]
param([string]$What = "all", [string]$Docx = "report\report.docx", [string]$Pptx = "slides\presentation.pptx")
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")

if ($What -in @("docx", "all")) {
  $docxPath = Join-Path $root $Docx
  $pdf = [IO.Path]::ChangeExtension($docxPath, ".pdf")
  $word = New-Object -ComObject Word.Application
  $word.Visible = $false
  $word.DisplayAlerts = 0
  try {
    $doc = $word.Documents.Open($docxPath, $false, $false, $false)
    foreach ($t in $doc.TablesOfContents) { $t.Update() }
    foreach ($t in $doc.TablesOfFigures) { $t.Update() }
    $doc.Fields.Update() | Out-Null
    $doc.Save()
    $doc.SaveAs2($pdf, 17)
    Write-Host "pages:" $doc.ComputeStatistics(2)
    $doc.Close()
  } finally { $word.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
  Write-Host "wrote $pdf"
}

if ($What -in @("pptx", "all")) {
  $pptxPath = Join-Path $root $Pptx
  $pdf = [IO.Path]::ChangeExtension($pptxPath, ".pdf")
  $pp = New-Object -ComObject PowerPoint.Application
  $pp.DisplayAlerts = 1
  try {
    $pres = $pp.Presentations.Open($pptxPath, $true, $false, $false)
    $pres.SaveAs($pdf, 32)
    $pres.Close()
  } finally { $pp.Quit() }
  Write-Host "wrote $pdf"
}
