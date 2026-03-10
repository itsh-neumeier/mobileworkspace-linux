param(
    [Parameter(Mandatory = $true)]
    [string]$UserName,

    [Parameter(Mandatory = $true)]
    [string]$Route,

    [ValidateSet("public", "internal")]
    [string]$Mode = "public",

    [ValidateSet("terminal", "desktop")]
    [string]$WorkspaceType = "terminal"
)

$servicePrefix = if ($WorkspaceType -eq "desktop") { "desktop" } else { "workspace" }
$serviceName = "$servicePrefix-$Route"
$envPrefix = ($Route -replace '[^A-Za-z0-9]', '_').ToUpperInvariant()
$networkName = if ($Mode -eq "internal") { "internal_net" } else { "public_net" }
$upstreamPort = if ($WorkspaceType -eq "desktop") { "3000" } else { "8080" }

Write-Host ""
Write-Host "Add these variables to .env:" -ForegroundColor Cyan
Write-Host "${envPrefix}_USER_NAME=$UserName"
Write-Host "${envPrefix}_USER_PASSWORD_HASH=CHANGE_ME"
if ($WorkspaceType -eq "terminal") {
    Write-Host "${envPrefix}_WORKSPACE_PASSWORD=CHANGE_ME"
}

Write-Host ""
Write-Host "Add this service to docker-compose.yml:" -ForegroundColor Cyan
if ($WorkspaceType -eq "terminal") {
@"
  $serviceName:
    image: lscr.io/linuxserver/code-server:4.104.2
    container_name: $serviceName
    restart: unless-stopped
    environment:
      PUID: 1000
      PGID: 1000
      TZ: Europe/Berlin
      PASSWORD: `${${envPrefix}_WORKSPACE_PASSWORD}
      SUDO_PASSWORD: `${${envPrefix}_WORKSPACE_PASSWORD}
      DEFAULT_WORKSPACE: /config/workspace
    volumes:
      - ./data/$Route/config:/config
    networks:
      - edge
      - $networkName
"@ | Write-Host
}
else {
@"
  $serviceName:
    image: lscr.io/linuxserver/webtop:ubuntu-kde
    container_name: $serviceName
    restart: unless-stopped
    shm_size: "1gb"
    environment:
      PUID: 1000
      PGID: 1000
      TZ: Europe/Berlin
      SUBFOLDER: /$Route/
      TITLE: $UserName Desktop
    volumes:
      - ./data/$Route/config:/config
    networks:
      - edge
      - $networkName
"@ | Write-Host
}

Write-Host ""
Write-Host "Add this route to Caddyfile:" -ForegroundColor Cyan
@"
	handle_path /$Route/* {
		basicauth {
			`${${envPrefix}_USER_NAME} `${${envPrefix}_USER_PASSWORD_HASH}
		}
		reverse_proxy $serviceName:$upstreamPort
	}
"@ | Write-Host
