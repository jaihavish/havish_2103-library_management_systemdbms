cd /d/denos/hp1/tmp
python build_report.py && powershell -File topdf.ps1 -In 'D:\denos\hp1\tmp\report_build.docx' -Out 'D:\denos\hp1\tmp\report_build.pdf' && python find_pages.py report_build.pdf >/dev/null
python build_report.py D:/denos/hp1/docs/Shreyash_Singh_DBMS_PBL_Report.docx && powershell -File topdf.ps1 -In 'D:\denos\hp1\docs\Shreyash_Singh_DBMS_PBL_Report.docx' -Out 'D:\denos\hp1\docs\Shreyash_Singh_DBMS_PBL_Report.pdf'
python find_pages.py D:/denos/hp1/docs/Shreyash_Singh_DBMS_PBL_Report.pdf > check.txt
echo done
