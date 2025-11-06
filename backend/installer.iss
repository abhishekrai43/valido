#define MyAppName "Valido"
#define MyAppVersion "1.0"
#define MyAppPublisher "Your Company"
#define MyAppURL "https://yourcompany.com"
#define MyAppExeName "valido.exe"

[Setup]
AppId={{12345678-1234-1234-1234-123456789ABC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename=valido-setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "serviceinstall"; Description: "Install as Windows Service"; GroupDescription: "Windows Service"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "frontend\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "nssm_install.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "service_pywin32.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\results"; Permissions: everyone-full
Name: "{app}\logs"; Permissions: everyone-full
Name: "{app}\data"; Permissions: everyone-full

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\nssm_install.bat"; Description: "Install Windows Service"; Tasks: serviceinstall; Flags: postinstall runascurrentuser
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "nssm"; Parameters: "stop Valido"; Flags: runhidden
Filename: "nssm"; Parameters: "remove Valido confirm"; Flags: runhidden

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create default configuration if it doesn't exist
    if not FileExists(ExpandConstant('{app}\valido.json')) then
    begin
      SaveStringToFile(ExpandConstant('{app}\valido.json'), '{}', False);
    end;
  end;
end;