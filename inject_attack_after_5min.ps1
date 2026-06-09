Set-Location "C:\Users\Batikha\Desktop\SMART GRID\smartgrid_simulation"

Write-Host "Waiting 5 minutes before injecting attack on SM_0042..."
Start-Sleep -Seconds 300

$attackRows = 10

for ($i = 1; $i -le $attackRows; $i++) {
    $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    Add-Content .\donnees_smart_meters.csv "$now,SM_0042,Zone B,commercial,38.500,265.00,145.300,ALERTE,False Data Injection"
    Add-Content .\alertes_smart_meters.csv "$now,SM_0042,Zone B,commercial,38.500,265.00,145.300,False Data Injection"

    Write-Host "Injected attack row $i/$attackRows at $now"

    Start-Sleep -Seconds 15
}

Write-Host "Attack injection completed."
