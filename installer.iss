#define MyAppName      "Veille Casting"
#define MyAppVersion   "1.0"
#define MyAppExeName   "VeilleCasting.exe"
#define MyTaskName     "VeilleCasting_2xJour"

[Setup]
AppId={{E8B3F5A1-9C2D-4B7E-A1F0-6D8E9C3B5A2D}}
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
  ApiKeyPage: TInputQueryWizardPage;
  SenderPage: TInputQueryWizardPage;

function IsNonEmpty(S: String): Boolean;
var
  L: String;
begin
  L := Trim(S);
  Result := Length(L) > 0;
end;

procedure InitializeWizard();
begin
  ApiKeyPage := CreateInputQueryPage(wpSelectDir,
    'Cle API Resend', 'Entrez votre cle API Resend',
    'Créez-la sur https://resend.com/api-keys');
  ApiKeyPage.Add('Cle API Resend :', True);

  SenderPage := CreateInputQueryPage(ApiKeyPage.ID,
    'Adresse d expediteur', 'Entrez l adresse d expediteur Resend',
    'Exemple : piccinno@hotmail.com');
  SenderPage.Add('Adresse expediteur :', False);
  SenderPage.Values[0] := 'piccinno@hotmail.com';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = ApiKeyPage.ID then
  begin
    if not IsNonEmpty(ApiKeyPage.Values[0]) then
    begin
      MsgBox('Entrez une cle API Resend valide.', mbError, MB_OK);
      Result := False;
    end;
  end;
  if CurPageID = SenderPage.ID then
  begin
    if not IsNonEmpty(SenderPage.Values[0]) then
    begin
      MsgBox('Entrez une adresse d expediteur valide.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if (PageID = ApiKeyPage.ID) or (PageID = SenderPage.ID) then
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
  CleanSender: String;
begin
  Dir := ExpandConstant('{userappdata}\VeilleCasting');
  ForceDirectories(Dir);
  FilePath := Dir + '\config.json';
  if FileExists(FilePath) then
    Exit;
  CleanSender := Trim(SenderPage.Values[0]);
  SetArrayLength(Lines, 53);
  Lines[0]  := '{';
  Lines[1]  := '  "resend_api_key": "' + JsonEscape(ApiKeyPage.Values[0]) + '",';
  Lines[2]  := '  "sender_email": "' + JsonEscape(CleanSender) + '",';
  Lines[3]  := '  "recipient_email": "piccinno@hotmail.com",';
  Lines[4]  := '  "zones_ok": [';
  Lines[5]  := '    "paca","provence","alpes","cote d''azur","bouches-du-rhone",';
  Lines[6]  := '    "var","vaucluse","alpes-maritimes","nice","marseille",';
  Lines[7]  := '    "toulon","avignon","cannes","aix-en-provence",';
  Lines[8]  := '    "frejus","menton","antibes","grasse","draguignan",';
  Lines[9]  := '    "istres","martigues","gap","manosque",';
  Lines[10] := '    "toute la france","france entiere","national"';
  Lines[11] := '  ],';
  Lines[12] := '  "category_keywords": [';
  Lines[13] := '    "figuration","figurant","figurante","casting","acteur",';
  Lines[14] := '    "actrice","comedien","comedienne","doublure","silhouette",';
  Lines[15] := '    "role muet","extra","film","serie","television","tv",';
  Lines[16] := '    "court-metrage","long-metrage","publicite","pub","clip",';
  Lines[17] := '    "clip video","theatre","spectacle","shooting",';
  Lines[18] := '    "campagne","marque","catalogue","e-commerce","commerce",';
  Lines[19] := '    "lookbook","mode"';
  Lines[20] := '  ],';
  Lines[21] := '  "exclude_keywords": [';
  Lines[22] := '    "animateur","animatrice","voix off","voice over",';
  Lines[23] := '    "danse","danseur","danseuse","chant","chanteur","chanteuse",';
  Lines[24] := '    "humour","stand up","podcast"';
  Lines[25] := '  ],';
  Lines[26] := '  "sources": {';
  Lines[27] := '    "castprod": true,';
  Lines[28] := '    "figurants_paca": true';
  Lines[29] := '  },';
  Lines[30] := '  "social_sources": {';
  Lines[31] := '    "facebook_public": {';
  Lines[32] := '      "enabled": true,';
  Lines[33] := '      "urls": [';
  Lines[34] := '        "https://www.facebook.com/groups/castingmarseille/",';
  Lines[35] := '        "https://www.facebook.com/groups/castingfigurantspaca/",';
  Lines[36] := '        "https://www.facebook.com/groups/figurantssud/"';
  Lines[37] := '      ]';
  Lines[38] := '    },';
  Lines[39] := '    "instagram_public": {';
  Lines[40] := '      "enabled": true,';
  Lines[41] := '      "hashtags": [';
  Lines[42] := '        "castingpaca",';
  Lines[43] := '        "castingmarseille",';
  Lines[44] := '        "figurantpaca",';
  Lines[45] := '        "modelepaca",';
  Lines[46] := '        "mannequinpaca",';
  Lines[47] := '        "seniormodele"';
  Lines[48] := '      ]';
  Lines[49] := '    }';
  Lines[50] := '  },';
  Lines[51] := '  "sleep_between_requests_seconds": 0.7';
  Lines[52] := '}';
  SaveStringsToUTF8File(FilePath, Lines, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    WriteConfigJson();
end;
