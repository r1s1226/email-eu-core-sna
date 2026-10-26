param([string]$ImgDir, [string]$NotesJson, [string]$Out, [string]$LinksJson = "")
# Build a 16:9 PPTX from full-slide images with speaker notes, using PowerPoint automation in a job with a timeout.
# Optional LinksJson: [{slide, left, top, width, height, url}] in points; each becomes a clear, clickable hyperlink area
# over the picture, since text inside the slide images cannot carry links.
Remove-Item $Out -ErrorAction SilentlyContinue
$job = Start-Job -ArgumentList $ImgDir, $NotesJson, $Out, $LinksJson -ScriptBlock {
    param($ImgDir, $NotesJson, $Out, $LinksJson)
    $notes = Get-Content $NotesJson -Raw -Encoding UTF8 | ConvertFrom-Json
    $links = @()
    if ($LinksJson) { $links = @(Get-Content $LinksJson -Raw -Encoding UTF8 | ConvertFrom-Json) }
    $imgs = Get-ChildItem $ImgDir -Filter '*.png' | Where-Object { $_.Name -notlike 'raw_*' } | Sort-Object Name
    if ($imgs.Count -ne $notes.Count) { throw "images $($imgs.Count) vs notes $($notes.Count)" }
    $pp = New-Object -ComObject PowerPoint.Application
    "powerpoint pid: " + (Get-Process POWERPNT | Sort-Object StartTime | Select-Object -Last 1).Id
    try {
        $pres = $pp.Presentations.Add(0)
        $pres.PageSetup.SlideWidth = 960
        $pres.PageSetup.SlideHeight = 540
        for ($i = 0; $i -lt $imgs.Count; $i++) {
            $s = $pres.Slides.Add($i + 1, 12)   # ppLayoutBlank
            $null = $s.Shapes.AddPicture($imgs[$i].FullName, 0, -1, 0, 0, 960, 540)
            $s.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text = ($notes[$i].notes -replace "`n", "`r")
        }
        foreach ($l in $links) {
            $r = $pres.Slides.Item([int]$l.slide).Shapes.AddShape(1, $l.left, $l.top, $l.width, $l.height)   # msoShapeRectangle
            $r.Fill.Visible = -1
            $r.Fill.ForeColor.RGB = 0
            $r.Fill.Transparency = 1.0   # fully clear but still clickable (a shape with no fill passes clicks through)
            $r.Line.Visible = 0
            $r.Name = "link: " + $l.url
            $r.ActionSettings.Item(1).Hyperlink.Address = $l.url   # ppMouseClick
            "link on slide $($l.slide): $($l.url)"
        }
        $pres.SaveAs($Out, 24)   # ppSaveAsOpenXMLPresentation
        "slides: " + $pres.Slides.Count
        $pres.Close()
    } finally {
        $pp.Quit()
    }
}
if (Wait-Job $job -Timeout 240) { Receive-Job $job } else { "TIMEOUT"; Receive-Job $job; Stop-Job $job }
Remove-Job $job -Force
