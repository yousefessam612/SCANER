; Inno Setup script for Iqra — offline document accessibility converter
; Build:  ISCC.exe installer.iss

#define MyAppName "Iqra"
#define MyAppNameAr "اقرأ"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Iqra Project"
#define MyAppExeName "Iqra.exe"
#define MyAppId "Iqra.DocumentAccess"

[Setup]
AppId=Iqra.DocumentAccess
AppName={#MyAppName} {#MyAppNameAr}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppNameAr} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/iqra-project/iqra
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName} {#MyAppNameAr}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=Iqra-Setup-{#MyAppVersion}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequired=admin
LicenseFile=LICENSE
; Bilingual setup dialog
ShowLanguageDialog=yes

[Languages]
Name: "ar"; MessagesFile: "compiler:Languages\Arabic.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
ar.CreateDesktopIcon=إنشاء أيقونة على سطح المكتب
ar.LaunchIqra=تشغيل اقرأ الآن
ar.CLITool=أداة سطر الأوامر (IqraCLI.exe)
en.CreateDesktopIcon=Create a &desktop icon
en.LaunchIqra=&Launch Iqra now
en.CLITool=Command-line tool (IqraCLI.exe)

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; application (PyInstaller onedir build + shared _internal)
Source: "dist\Iqra\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; documentation
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "USER_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "ACCESSIBILITY_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "ARCHITECTURE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "TROUBLESHOOTING.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName} {#MyAppNameAr}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "https://github.com/iqra-project/iqra"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName} {#MyAppNameAr}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchIqra}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; remove user settings only when the user confirms (kept by default)
; Type: filesandordirs; Name: "{userappdata}\Iqra"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
