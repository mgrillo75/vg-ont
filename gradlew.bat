@rem
@rem Copyright 2015 the original author or authors.
@rem
@rem Licensed under the Apache License, Version 2.0 (the "License");
@rem you may not use this file except in compliance with the License.
@rem You may obtain a copy of the License at
@rem
@rem      https://www.apache.org/licenses/LICENSE-2.0
@rem
@rem Unless required by applicable law or agreed to in writing, software
@rem distributed under the License is distributed on an "AS IS" BASIS,
@rem WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
@rem See the License for the specific language governing permissions and
@rem limitations under the License.
@rem

@if "%DEBUG%" == "" @echo off
@rem ##########################################################################
@rem
@rem  Gradle startup script for Windows
@rem
@rem ##########################################################################

@rem Set local scope for the variables with windows NT shell
if "%OS%"=="Windows_NT" setlocal

@rem ##########################################################################
@rem Foundry-specific setup
@rem ##########################################################################

set _root_dir=%~dp0
set root_dir=%_root_dir:~0,-1%

set NEEDS_LOCAL_FOUNDRY_SETUP=
if "%JEMMA%" == "" set NEEDS_LOCAL_FOUNDRY_SETUP=TRUE
if not defined ORG_GRADLE_PROJECT_bearerToken set NEEDS_LOCAL_FOUNDRY_SETUP=TRUE
if not defined ORG_GRADLE_PROJECT_externalUri set NEEDS_LOCAL_FOUNDRY_SETUP=TRUE
if not defined ORG_GRADLE_PROJECT_repoRid set NEEDS_LOCAL_FOUNDRY_SETUP=TRUE
if not defined gradleDistributionUrl set NEEDS_LOCAL_FOUNDRY_SETUP=TRUE

if defined NEEDS_LOCAL_FOUNDRY_SETUP (
  setlocal EnableDelayedExpansion

  if defined FOUNDRY_HOSTNAME (
    if defined FOUNDRY_USERNAME (
      if defined FOUNDRY_TOKEN (
        echo "Environment variables [FOUNDRY_HOSTNAME, FOUNDRY_USERNAME, FOUNDRY_TOKEN] are already set. Using them"
        set GIT_REMOTE_HOST=%FOUNDRY_HOSTNAME%
        set GIT_REMOTE_USERNAME=%FOUNDRY_USERNAME%
        set GIT_REMOTE_PASSWORD=%FOUNDRY_TOKEN%
      )
    )
  ) else (
      echo "Environment variables [FOUNDRY_HOSTNAME, FOUNDRY_USERNAME, FOUNDRY_TOKEN] are not set. Attempting to infer from Git remote url"
      @rem Parse the Git remote via PowerShell so URL-encoded usernames such as %40
      @rem are not mangled by cmd.exe variable expansion.
      for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $remote = git config --get remote.origin.url; if ([string]::IsNullOrWhiteSpace($remote)) { throw 'Git remote url not set.' }; $uri = [System.Uri]$remote; $parts = $uri.UserInfo.Split(':', 2); if ($parts.Length -lt 2 -or [string]::IsNullOrWhiteSpace($uri.Authority)) { throw 'Git remote url must include username, token, and host.' }; Write-Output ('FOUNDRY_HOST=' + $uri.Authority); Write-Output ('FOUNDRY_USERNAME=' + [System.Uri]::UnescapeDataString($parts[0])); Write-Output ('FOUNDRY_TOKEN=' + $parts[1])"`) do (
        for /f "tokens=1* delims==" %%B in ("%%A") do (
          if "%%B"=="FOUNDRY_HOST" set "GIT_REMOTE_HOST=%%C"
          if "%%B"=="FOUNDRY_USERNAME" set "GIT_REMOTE_USERNAME=%%C"
          if "%%B"=="FOUNDRY_TOKEN" set "GIT_REMOTE_PASSWORD=%%C"
        )
      )
      if not defined GIT_REMOTE_HOST (
        echo Warning: Git remote url not set.
        echo Please ensure the following environment variables are set [FOUNDRY_HOSTNAME, FOUNDRY_USERNAME, FOUNDRY_TOKEN]
        exit /b 1
      )
      if not defined GIT_REMOTE_PASSWORD (
        echo Warning: Git remote url does not include a bearer token.
        echo Please ensure the following environment variables are set [FOUNDRY_HOSTNAME, FOUNDRY_USERNAME, FOUNDRY_TOKEN]
        exit /b 1
      )
  )

  set ORG_GRADLE_PROJECT_externalUri=https://!GIT_REMOTE_HOST!

  set ORG_GRADLE_PROJECT_bearerToken=!GIT_REMOTE_PASSWORD!
  set ORG_GRADLE_PROJECT_isRunningLocally=TRUE
  for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $token = $env:ORG_GRADLE_PROJECT_bearerToken; $parts = $token.Split('.'); if ($parts.Length -ne 3) { exit 1 }; $payload = $parts[1].Replace('-', '+').Replace('_', '/'); switch ($payload.Length %% 4) { 0 { } 2 { $payload += '==' } 3 { $payload += '=' } default { exit 1 } }; $json = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($payload)); $exp = ($json | ConvertFrom-Json).exp; if (-not $exp) { exit 1 }; $ttl = [DateTimeOffset]::FromUnixTimeSeconds([int64]$exp) - [DateTimeOffset]::UtcNow; if ($ttl.TotalMinutes -gt 5) { Write-Output 'TRUE' }"`) do (
    set "SKIP_LOCAL_AUTH_PLUGIN=%%A"
  )
  if defined SKIP_LOCAL_AUTH_PLUGIN (
    echo "Bearer token already has more than 5 minutes of TTL. Skipping local auth refresh"
    set ORG_GRADLE_PROJECT_isRunningLocally=FALSE
  )

  if not defined ORG_GRADLE_PROJECT_repoRid (
    for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "$ErrorActionPreference='Stop'; foreach ($line in Get-Content '%root_dir%\gradle.properties') { if ($line -match '^\s*repositoryRid\s*=\s*(.+?)\s*$') { Write-Output $Matches[1]; exit 0 } }; exit 1"`) do (
      set "ORG_GRADLE_PROJECT_repoRid=%%A"
    )
  )

  set ORG_GRADLE_PROJECT_nodeDistUri=!ORG_GRADLE_PROJECT_externalUri!/assets/dyn/nodejs-bundle
  set ORG_GRADLE_PROJECT_functionRegistryApiUri=!ORG_GRADLE_PROJECT_externalUri!/function-registry/api
  set ORG_GRADLE_PROJECT_ontologyMetadataApiUri=!ORG_GRADLE_PROJECT_externalUri!/ontology-metadata/api
  set ORG_GRADLE_PROJECT_compassApiUri=!ORG_GRADLE_PROJECT_externalUri!/compass/api
  set ORG_GRADLE_PROJECT_actionsApiUri=!ORG_GRADLE_PROJECT_externalUri!/actions/api
  set ORG_GRADLE_PROJECT_artifactsApiUri=!ORG_GRADLE_PROJECT_externalUri!/artifacts/api
  set ORG_GRADLE_PROJECT_opusServerApiUri=!ORG_GRADLE_PROJECT_externalUri!/opus-server/api
  set ORG_GRADLE_PROJECT_bellasoApiUri=!ORG_GRADLE_PROJECT_externalUri!/bellaso/api
  set ORG_GRADLE_PROJECT_foundryMlApiUri=!ORG_GRADLE_PROJECT_externalUri!/foundry-ml/api
  set ORG_GRADLE_PROJECT_foundryMlLiveApiUri=!ORG_GRADLE_PROJECT_externalUri!/foundry-ml-live/api
  set ORG_GRADLE_PROJECT_modelsApiUri=!ORG_GRADLE_PROJECT_externalUri!/models/api
  set ORG_GRADLE_PROJECT_webhooksApiUri=!ORG_GRADLE_PROJECT_externalUri!/webhooks/api
  set ORG_GRADLE_PROJECT_multipassApiUri=!ORG_GRADLE_PROJECT_externalUri!/multipass/api
  set ORG_GRADLE_PROJECT_jemmaApiUri=!ORG_GRADLE_PROJECT_externalUri!/jemma/api
  set ORG_GRADLE_PROJECT_magritteCoordinatorApiUri=!ORG_GRADLE_PROJECT_externalUri!/magritte-coordinator/api
  set ORG_GRADLE_PROJECT_languageModelServiceApiUri=!ORG_GRADLE_PROJECT_externalUri!/language-model-service/api
  set ORG_GRADLE_PROJECT_thirdPartyApplicationServiceApiUri=!ORG_GRADLE_PROJECT_externalUri!/third-party-application-service/api
  set ORG_GRADLE_PROJECT_functionExecutorApiUri=!ORG_GRADLE_PROJECT_externalUri!/function-executor/api

  if not defined JAVA_HOME (
    for /f "tokens=2 delims==" %%J in ('java -XshowSettings:properties -version 2^>^&1 ^| findstr /C:"java.home ="') DO (
      set "_JAVA_HOME_FROM_PATH=%%J"
    )
    if defined _JAVA_HOME_FROM_PATH (
      for /f "tokens=* delims= " %%J in ("!_JAVA_HOME_FROM_PATH!") DO (
        set "JAVA_HOME=%%J"
      )
    )
  )

  if exist "!JAVA_HOME!\jre\lib\security\cacerts" (
    if not defined ORG_GRADLE_PROJECT_trustStore (
        set ORG_GRADLE_PROJECT_trustStore=!JAVA_HOME!\jre\lib\security\cacerts
    )
  ) else if exist "!JAVA_HOME!\lib\security\cacerts" (
    if not defined ORG_GRADLE_PROJECT_trustStore (
        set ORG_GRADLE_PROJECT_trustStore=!JAVA_HOME!\lib\security\cacerts
    )
  )

  if defined ORG_GRADLE_PROJECT_trustStore (
    set JAVA_OPTS=-Djavax.net.ssl.trustStore="!ORG_GRADLE_PROJECT_trustStore!"
  )
  set wrapperAuthGradleOptions=-Dgradle.wrapperUser="!GIT_REMOTE_USERNAME!" -Dgradle.wrapperPassword="!GIT_REMOTE_PASSWORD!"
  if ["%GRADLE_OPTS%"]==[""] set GRADLE_OPTS=
  set GRADLE_OPTS=%GRADLE_OPTS% !wrapperAuthGradleOptions!
  set gradleDistributionUrl=!ORG_GRADLE_PROJECT_externalUri!/assets/dyn/gradle-distributions/gradle-7.6.4-bin.zip
)

set "wrapperTemplatePropsFile=%root_dir%\gradle\wrapper\gradle-wrapper.template.properties"
set "wrapperPropsFile=%root_dir%\gradle\wrapper\gradle-wrapper.properties"
if exist "%wrapperPropsFile%" del "%wrapperPropsFile%"
for /f "usebackq tokens=*" %%A in ("%wrapperTemplatePropsFile%") do (
    set "line=%%A"
    set "line=!line:${gradleDistributionUrl}=%gradleDistributionUrl%!"
    <nul set /p "=!line!" >> "%wrapperPropsFile%"
    echo.>>"%wrapperPropsFile%"
)

@rem ##########################################################################

set DIRNAME=%~dp0
if "%DIRNAME%" == "" set DIRNAME=.
set APP_BASE_NAME=%~n0
set APP_HOME=%DIRNAME%

@rem Resolve any "." and ".." in APP_HOME to make it shorter.
for %%i in ("%APP_HOME%") do set APP_HOME=%%~fi

@rem Add default JVM options here. You can also use JAVA_OPTS and GRADLE_OPTS to pass JVM options to this script.
set DEFAULT_JVM_OPTS="-Xmx64m" "-Xms64m"

@rem Find java.exe
if defined JAVA_HOME goto findJavaFromJavaHome

set JAVA_EXE=java.exe
%JAVA_EXE% -version >NUL 2>&1
if "%ERRORLEVEL%" == "0" goto execute

echo.
echo ERROR: JAVA_HOME is not set and no 'java' command could be found in your PATH.
echo.
echo Please set the JAVA_HOME variable in your environment to match the
echo location of your Java installation.

goto fail

:findJavaFromJavaHome
set JAVA_HOME=%JAVA_HOME:"=%
set JAVA_EXE=%JAVA_HOME%/bin/java.exe

if exist "%JAVA_EXE%" goto execute

echo.
echo ERROR: JAVA_HOME is set to an invalid directory: %JAVA_HOME%
echo.
echo Please set the JAVA_HOME variable in your environment to match the
echo location of your Java installation.

goto fail

:execute
@rem Setup the command line

set CLASSPATH=%APP_HOME%\gradle\wrapper\gradle-wrapper.jar


@rem Execute Gradle
if defined NEEDS_LOCAL_FOUNDRY_SETUP (
  "%JAVA_EXE%" %DEFAULT_JVM_OPTS% %JAVA_OPTS% !GRADLE_OPTS! "-Dorg.gradle.appname=%APP_BASE_NAME%" -classpath "%CLASSPATH%" org.gradle.wrapper.GradleWrapperMain %*
) else (
  "%JAVA_EXE%" %DEFAULT_JVM_OPTS% %JAVA_OPTS% %GRADLE_OPTS% "-Dorg.gradle.appname=%APP_BASE_NAME%" -classpath "%CLASSPATH%" org.gradle.wrapper.GradleWrapperMain %*
)

:end
@rem End local scope for the variables with windows NT shell
if "%ERRORLEVEL%"=="0" goto mainEnd

:fail
rem Set variable GRADLE_EXIT_CONSOLE if you need the _script_ return code instead of
rem the _cmd.exe /c_ return code!
if  not "" == "%GRADLE_EXIT_CONSOLE%" exit 1
exit /b 1

:mainEnd
if "%OS%"=="Windows_NT" endlocal

:omega
