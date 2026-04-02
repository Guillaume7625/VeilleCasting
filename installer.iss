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
  OpenAIPage: TInputQueryWizardPage;

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

  OpenAIPage := CreateInputQueryPage(SenderPage.ID,
    'IA OpenAI (optionnel)', 'Amelioration IA des annonces',
    'Laissez vide pour fonctionner sans IA.');
  OpenAIPage.Add('Cle API OpenAI :', False);
  OpenAIPage.Add('Modele OpenAI :', False);
  OpenAIPage.Values[0] := '';
  OpenAIPage.Values[1] := 'gpt-5.1-mini';
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
  if CurPageID = OpenAIPage.ID then
  begin
    if not IsNonEmpty(OpenAIPage.Values[0]) then
      OpenAIPage.Values[1] := 'gpt-5.1-mini';
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if (PageID = ApiKeyPage.ID) or (PageID = SenderPage.ID) or (PageID = OpenAIPage.ID) then
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
  CleanOpenAIKey: String;
  CleanOpenAIModel: String;
begin
  Dir := ExpandConstant('{userappdata}\VeilleCasting');
  ForceDirectories(Dir);
  FilePath := Dir + '\config.json';
  if FileExists(FilePath) then
    Exit;
  CleanSender := Trim(SenderPage.Values[0]);
  CleanOpenAIKey := Trim(OpenAIPage.Values[0]);
  CleanOpenAIModel := Trim(OpenAIPage.Values[1]);
  SetArrayLength(Lines, 55);
  Lines[0]  := '{';
  Lines[1]  := '  "resend_api_key": "' + JsonEscape(ApiKeyPage.Values[0]) + '",';
  Lines[2]  := '  "sender_email": "' + JsonEscape(CleanSender) + '",';
  Lines[3]  := '  "recipient_email": "piccinno@hotmail.com",';
  Lines[4]  := '  "openai_api_key": "' + JsonEscape(CleanOpenAIKey) + '",';
  Lines[5]  := '  "openai_model": "' + JsonEscape(CleanOpenAIModel) + '",';
  Lines[6]  := '  "zones_ok": [';
  Lines[7]  := '    "paca","provence","alpes","cote d''azur","bouches-du-rhone",';
  Lines[8]  := '    "var","vaucluse","alpes-maritimes","nice","marseille",';
  Lines[9]  := '    "toulon","avignon","cannes","aix-en-provence",';
  Lines[10] := '    "frejus","menton","antibes","grasse","draguignan",';
  Lines[11] := '    "istres","martigues","gap","manosque",';
  Lines[12] := '    "toute la france","france entiere","national"';
  Lines[13] := '  ],';
  Lines[14] := '  "category_keywords": [';
  Lines[15] := '    "figuration","figurant","figurante","casting","acteur",';
  Lines[16] := '    "actrice","comedien","comedienne","doublure","silhouette",';
  Lines[17] := '    "role muet","extra","film","serie","television","tv",';
  Lines[18] := '    "court-metrage","long-metrage","publicite","pub","clip",';
  Lines[19] := '    "clip video","theatre","spectacle","shooting",';
  Lines[20] := '    "campagne","marque","catalogue","e-commerce","commerce",';
  Lines[21] := '    "lookbook","mode"';
  Lines[22] := '  ],';
  Lines[23] := '  "exclude_keywords": [';
  Lines[24] := '    "animateur","animatrice","voix off","voice over",';
  Lines[25] := '    "danse","danseur","danseuse","chant","chanteur","chanteuse",';
  Lines[26] := '    "humour","stand up","podcast"';
  Lines[27] := '  ],';
  Lines[28] := '  "sources": {';
  Lines[29] := '    "castprod": true,';
  Lines[30] := '    "figurants_paca": true';
  Lines[31] := '  },';
  Lines[32] := '  "social_sources": {';
  Lines[33] := '    "facebook_public": {';
  Lines[34] := '      "enabled": true,';
  Lines[35] := '      "urls": [';
  Lines[36] := '        "https://www.facebook.com/groups/castingmarseille/",';
  Lines[37] := '        "https://www.facebook.com/groups/castingfigurantspaca/",';
  Lines[38] := '        "https://www.facebook.com/groups/figurantssud/"';
  Lines[39] := '      ]';
  Lines[40] := '    },';
  Lines[41] := '    "instagram_public": {';
  Lines[42] := '      "enabled": true,';
  Lines[43] := '      "hashtags": [';
  Lines[44] := '        "castingpaca",';
  Lines[45] := '        "castingmarseille",';
  Lines[46] := '        "figurantpaca",';
  Lines[47] := '        "modelepaca",';
  Lines[48] := '        "mannequinpaca",';
  Lines[49] := '        "seniormodele"';
  Lines[50] := '      ]';
  Lines[51] := '    }';
  Lines[52] := '  },';
  Lines[53] := '  "sleep_between_requests_seconds": 0.7';
  Lines[54] := '}';
  SaveStringsToUTF8File(FilePath, Lines, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    WriteConfigJson();
end;
