param(
    [Parameter(Mandatory = $true)]
    [string]$InputDocx,

    [Parameter(Mandatory = $true)]
    [string]$OutputJson
)

$ErrorActionPreference = 'Stop'

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

try {
    $doc = $word.Documents.Open($InputDocx, $false, $true)
    $doc.Repaginate()

    $items = [System.Collections.Generic.List[object]]::new()
    $paragraphCount = $doc.Paragraphs.Count

    for ($i = 1; $i -le $paragraphCount; $i++) {
        $paragraph = $doc.Paragraphs.Item($i)
        $range = $paragraph.Range.Duplicate
        $text = $range.Text -replace "[\r\a]", ''
        $text = $text.Trim()
        if ([string]::IsNullOrWhiteSpace($text)) {
            continue
        }

        $style = ''
        try {
            $style = [string]$range.Style.NameLocal
        }
        catch {
            $style = [string]$range.Style
        }

        $isRelevant = $style -like '*Heading*' -or
            $style -eq 'Caption' -or
            $text -match '^(สารบัญ|รูปที่|ตารางที่|บทที่|บรรณานุกรม|ภาคผนวก|ประวัติผู้เขียน)'

        if (-not $isRelevant) {
            continue
        }

        $startRange = $range.Duplicate
        $startRange.Collapse(1)

        $listString = ''
        try {
            $listString = [string]$paragraph.Range.ListFormat.ListString
        }
        catch {
            $listString = ''
        }

        $items.Add([pscustomobject]@{
            index = $i
            text = $text
            style = $style
            outline_level = [int]$paragraph.OutlineLevel
            list_string = $listString
            absolute_page = [int]$startRange.Information(3)
            adjusted_page = [int]$startRange.Information(1)
            section = [int]$startRange.Information(2)
        })
    }

    $result = [pscustomobject]@{
        input = (Resolve-Path -LiteralPath $InputDocx).Path
        page_count = [int]$doc.ComputeStatistics(2)
        paragraph_count = [int]$paragraphCount
        items = $items
    }

    $json = $result | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText($OutputJson, $json, [System.Text.UTF8Encoding]::new($false))
    $doc.Close(0)
}
finally {
    $word.Quit()
}
