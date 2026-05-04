#define MyAppName "Sakura NoteForge"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\windows\SakuraNoteForge"
#endif
#ifndef InstallerIconFile
  #define InstallerIconFile "..\assets\noteforge_icon.ico"
#endif

[Setup]
AppId={{F3A72B1C-8D4E-4F9A-BC2E-7A1D5E3F9C82}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher=Sakura Project
AppPublisherURL=https://github.com/cxc02374/Sakura-NoteFoge
DefaultDirName={autopf}\Sakura NoteForge
DefaultGroupName=Sakura NoteForge
OutputDir=..\dist\installer
OutputBaseFilename=SakuraNoteForge_Setup_{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
SetupIconFile={#InstallerIconFile}
UninstallDisplayIcon={app}\SakuraNoteForge.exe
MinVersion=10.0

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Sakura NoteForge"; Filename: "{app}\SakuraNoteForge.exe"
Name: "{userdesktop}\Sakura NoteForge"; Filename: "{app}\SakuraNoteForge.exe"

[Run]
Filename: "{app}\SakuraNoteForge.exe"; Description: "Sakura NoteForge を起動"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
