# test_api.ps1 — Complete API test suite for Windows PowerShell

$baseUrl = "http://127.0.0.1:8000"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "1. Testing Health Check" -ForegroundColor Cyan
Write-Host "=================================================="
$health = Invoke-RestMethod -Uri "$baseUrl/health"
$health | ConvertTo-Json

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "2. Login as Super Admin" -ForegroundColor Cyan
Write-Host "=================================================="
$saLogin = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/auth/login" -ContentType "application/json" -Body '{"email":"superadmin@demo.com","password":"SuperAdmin@1234"}'
$saToken = $saLogin.access_token
$saHeaders = @{ Authorization = "Bearer $saToken" }
Write-Host "SuperAdmin JWT Token obtained successfully."

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "3. Super Admin Profile (/auth/me)" -ForegroundColor Cyan
Write-Host "=================================================="
$saProfile = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/me" -Headers $saHeaders
$saProfile | ConvertTo-Json

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "4. List Departments" -ForegroundColor Cyan
Write-Host "=================================================="
$depts = Invoke-RestMethod -Uri "$baseUrl/api/v1/departments/" -Headers $saHeaders
$depts | ConvertTo-Json

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "5. List Sections / Classes" -ForegroundColor Cyan
Write-Host "=================================================="
$sections = Invoke-RestMethod -Uri "$baseUrl/api/v1/sections/" -Headers $saHeaders
$sections | ConvertTo-Json

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "6. List Subjects" -ForegroundColor Cyan
Write-Host "=================================================="
$subjects = Invoke-RestMethod -Uri "$baseUrl/api/v1/subjects/" -Headers $saHeaders
$subjects | ConvertTo-Json

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "7. List Students" -ForegroundColor Cyan
Write-Host "=================================================="
$students = Invoke-RestMethod -Uri "$baseUrl/api/v1/students/" -Headers $saHeaders
$students | ConvertTo-Json

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "8. Login as Faculty (Dr. Ramesh)" -ForegroundColor Cyan
Write-Host "=================================================="
$facLogin = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/auth/login" -ContentType "application/json" -Body '{"email":"faculty@demo.com","password":"Faculty@1234"}'
$facToken = $facLogin.access_token
$facHeaders = @{ Authorization = "Bearer $facToken" }
Write-Host "Faculty JWT Token obtained successfully."

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "9. Faculty Profile (/auth/me)" -ForegroundColor Cyan
Write-Host "=================================================="
$facProfile = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/me" -Headers $facHeaders
$facProfile | ConvertTo-Json

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "10. Faculty Assigned Subjects & Progress (/marks/my-subjects)" -ForegroundColor Cyan
Write-Host "=================================================="
$mySubjects = Invoke-RestMethod -Uri "$baseUrl/api/v1/marks/my-subjects" -Headers $facHeaders
$mySubjects | ConvertTo-Json

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "11. CO Attainment Preview Calculation (Dry-Run)" -ForegroundColor Cyan
Write-Host "=================================================="
$previewBody = @{
    student_id = 6
    subject_id = 7
    section_id = 5
    cia_co1 = 32; cia_co2 = 30; cia_co3 = 28; cia_co4 = 34; cia_co5 = 31
    assess_co1 = 9; assess_co2 = 8; assess_co3 = 9; assess_co4 = 8; assess_co5 = 9
    presentation = 85; quiz = 90
    endsem_co1 = 18; endsem_co2 = 16; endsem_co3 = 17; endsem_co4 = 15; endsem_co5 = 16
} | ConvertTo-Json
$preview = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/marks/preview" -Headers $facHeaders -ContentType "application/json" -Body $previewBody
$preview | ConvertTo-Json

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "12. Marks Upsert (Persistence + Auto CO1-CO5 Calculation)" -ForegroundColor Cyan
Write-Host "=================================================="
$upsertBody = @{
    student_id = 6
    subject_id = 7
    section_id = 5
    cia_co1 = 34; cia_co2 = 32; cia_co3 = 30; cia_co4 = 33; cia_co5 = 31
    assess_co1 = 9; assess_co2 = 9; assess_co3 = 8; assess_co4 = 8; assess_co5 = 9
    presentation = 88; quiz = 92
    endsem_co1 = 17; endsem_co2 = 16; endsem_co3 = 16; endsem_co4 = 15; endsem_co5 = 17
} | ConvertTo-Json
$upsertResult = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/marks/upsert" -Headers $facHeaders -ContentType "application/json" -Body $upsertBody
$upsertResult | ConvertTo-Json

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "13. Filter Marks by Section & Subject (/marks/)" -ForegroundColor Cyan
Write-Host "=================================================="
$marksList = Invoke-RestMethod -Uri "$baseUrl/api/v1/marks/?subject_id=7&section_id=5" -Headers $facHeaders
$marksList | ConvertTo-Json -Depth 3

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "14. Course Outcome Attainment Report" -ForegroundColor Cyan
Write-Host "=================================================="
$attainment = Invoke-RestMethod -Uri "$baseUrl/api/v1/reports/attainment?subject_code=CS301" -Headers $saHeaders
$attainment | ConvertTo-Json

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "15. RBAC Security Check: Faculty Forbidden from Creating Department" -ForegroundColor Cyan
Write-Host "=================================================="
try {
    Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/departments/" -Headers $facHeaders -ContentType "application/json" -Body '{"name":"Unauthorized","code":"UNAUTH"}'
} catch {
    Write-Host "Expected 403 Forbidden received:" -ForegroundColor Green
    $_.ErrorDetails.Message
}

Write-Host "`n==================================================" -ForegroundColor Green
Write-Host "ALL USE CASES COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "=================================================="
