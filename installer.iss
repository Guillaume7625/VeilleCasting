#define MyAppName      "Veille Casting"
#define MyAppVersion   "1.0"
#define MyAppExeName   "VeilleCasting.exe"
#define MyTaskName     "VeilleCasting_2xJour"

[Setup]
AppId={{E8B3F5A1-9C2D-4B7E-A1F0-6D8E9C3B5A2D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\VeilleCasting
DefaultGroupName={#MyAppName}
OutputBaseFilename=VeilleCasting_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
SetupIconFile=compiler:SetupClassicIcon.ico

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "create_task.ps1"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\Configurer {#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--init"
Name: "{group}\Lancer maintenant"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--once"
Name: "{group}\Desinstaller {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{sysnative}\WindowsPowerShell\v1.0\powershell.exe"; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{tmp}\create_task.ps1"" -ExePath ""{app}\{#MyAppExeName}"" -TaskName ""{#MyTaskName}"""; \
    StatusMsg: "Creation de la tache planifiee..."; \
    Flags: runhidden
Filename: "{app}\{#MyAppExeName}"; \
    Parameters: "--once"; \
    Description: "Lancer une premiere veille maintenant"; \
    Flags: postinstall skipifsilent nowait

[UninstallRun]
Filename: "{sysnative}\WindowsPowerShell\v1.0\powershell.exe"; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""Unregister-ScheduledTask -TaskName '{#MyTaskName}' -Confirm:$false -ErrorAction SilentlyContinue"""; \
    Flags: runhidden

[Code]
var
  GmailPage: TInputQueryWizardPage;
  PasswordPage: TInputQueryWizardPage;

function IsGmail(S: String): Boolean;
var
  L: String;
begin
  L := Lowercase(S);
  Result := (Pos('@gmail.com', L) > 0) or (Pos('@googlemail.com', L) > 0);
end;

function StripSpaces(S: String): String;
var
  I: Integer;
begin
  Result := '';
  for I := 1 to Length(S) do
    if S[I] <> ' ' then
      Result := Result + S[I];
end;

procedure InitializeWizard();
begin
  GmailPage := CreateInputQueryPage(wpSelectDir,
    'Adresse Gmail', 'Entrez votre adresse Gmail (expediteur)',
    'Cette adresse servira a envoyer les alertes casting.');
  GmailPage.Add('Adresse Gmail :', False);

  PasswordPage := CreateInputQueryPage(GmailPage.ID,
    'Mot de passe application', 'Entrez le mot de passe application Gmail (16 caracteres)',
    'Creez-le sur https://myaccount.google.com/apppasswords');
  PasswordPage.Add('Mot de passe :', True);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Clean: String;
begin
  Result := True;
  if CurPageID = GmailPage.ID then
  begin
    if not IsGmail(GmailPage.Values[0]) then
    begin
      MsgBox('Entrez une adresse @gmail.com ou @googlemail.com valide.', mbError, MB_OK);
      Result := False;
    end;
  end;
  if CurPageID = PasswordPage.ID then
  begin
    Clean := StripSpaces(PasswordPage.Values[0]);
    if Length(Clean) <> 16 then
    begin
      MsgBox('Le mot de passe application doit faire 16 caracteres (sans espaces).', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if (PageID = GmailPage.ID) or (PageID = PasswordPage.ID) then
  begin
    if FileExists(ExpandConstant('{userappdata}\VeilleCasting\config.json')) then
      Result := True;
  end;
end;

function JsonEscape(S: String): String;
begin
  StringChangeEx(S, '\', '\\', True);
  StringChangeEx(S, '"', '\"', True);
  Result := S;
end;

procedure WriteConfigJson();
var
  Dir, FilePath: String;
  Lines: TArrayOfString;
  CleanPwd: String;
begin
  Dir := ExpandConstant('{userappdata}\VeilleCasting');
  ForceDirectories(Dir);
  FilePath := Dir + '\config.json';
  if FileExists(FilePath) then
    Exit;
  CleanPwd := StripSpaces(PasswordPage.Values[0]);
  SetArrayLength(Lines, 39);
  Lines[0]  := '{';
  Lines[1]  := '  "sender_email": "' + JsonEscape(GmailPage.Values[0]) + '",';
  Lines[2]  := '  "sender_password": "' + JsonEscape(CleanPwd) + '",';
  Lines[3]  := '  "smtp_server": "smtp.gmail.com",';
  Lines[4]  := '  "smtp_port": 587,';
  Lines[5]  := '  "recipient_email": "piccinno@hotmail.com",';
  Lines[6]  := '  "zones_ok": [';
  Lines[7]  := '    "paca","provence","alpes","cote d''azur","bouches-du-rhone",';
  Lines[8]  := '    "var","vaucluse","alpes-maritimes","nice","marseille",';
  Lines[9]  := '    "toulon","avignon","cannes","aix-en-provence",';
  Lines[10] := '    "occitanie","montpellier","toulouse","nimes","perpignan",';
  Lines[11] := '    "beziers","herault","gard","aude","pyrenees-orientales",';
  Lines[12] := '    "haute-garonne","tarn","ariege","lot","aveyron","gers",';
  Lines[13] := '    "tarn-et-garonne","hautes-pyrenees","lozere",';
  Lines[14] := '    "toute la france","france entiere","national"';
  Lines[15] := '  ],';
  Lines[16] := '  "category_keywords": [';
  Lines[17] := '    "figuration","figurant","figurante","casting","acteur",';
  Lines[18] := '    "actrice","comedien","comedienne","doublure","silhouette",';
  Lines[19] := '    "role muet","extra","film","serie","television","tv",';
  Lines[20] := '    "court-metrage","long-metrage","publicite","pub","clip",';
  Lines[21] := '    "clip video","theatre","spectacle"';
  Lines[22] := '  ],';
  Lines[23] := '  "exclude_keywords": [';
  Lines[24] := '    "mannequin","model","modele","photo","photographe",';
  Lines[25] := '    "animateur","animatrice","voix off","voice over",';
  Lines[26] := '    "danse","danseur","danseuse","chant","chanteur","chanteuse"';
  Lines[27] := '  ],';
  Lines[28] := '  "sources": {';
  Lines[29] := '    "castprod": true,';
  Lines[30] := '    "figurants_paca": true,';
  Lines[31] := '    "figurants_occitanie": true,';
  Lines[32] := '    "occitanie_films": true';
  Lines[33] := '  },';
  Lines[34] := '  "sleep_between_requests_seconds": 0.7';
  Lines[35] := '}';
  { trim array }
  SetArrayLength(Lines, 36);
  SaveStringsToUTF8File(FilePath, Lines, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    WriteConfigJson();
end;
