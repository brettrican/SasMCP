# Requires WiX Toolset (https://wixtoolset.org/) installed and added to PATH
# Usage: Run this script from the project root

$ProductName = "SassyMCP"
$ProductVersion = "1.2.0"
$Manufacturer = "SassyMCP Contributors"
$SourceDir = "dist/Most recent extract"
$OutputMsi = "SassyMCP-v1.2.0.msi"
$WxsFile = "installer.wxs"

# Generate WiX XML (WXS) file
echo "Generating $WxsFile..."

$wxs = @"
<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" Name="$ProductName" Language="1033" Version="$ProductVersion" Manufacturer="$Manufacturer" UpgradeCode="$(New-Guid)">
    <Package InstallerVersion="500" Compressed="yes" InstallScope="perMachine" />
    <MajorUpgrade DowngradeErrorMessage="A newer version of $ProductName is already installed." />
    <MediaTemplate />
    <Feature Id="ProductFeature" Title="$ProductName" Level="1">
      <ComponentGroupRef Id="AppFiles" />
    </Feature>
  </Product>
  <Fragment>
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFilesFolder">
        <Directory Id="INSTALLFOLDER" Name="$ProductName" />
      </Directory>
    </Directory>
  </Fragment>
  <Fragment>
    <ComponentGroup Id="AppFiles" Directory="INSTALLFOLDER">
"@

# Recursively add files from the source directory
$files = Get-ChildItem -Path "$SourceDir" -Recurse -File
foreach ($file in $files) {
    $relPath = $file.FullName.Substring((Resolve-Path "$SourceDir").Path.Length + 1).Replace("\", "/")
    $guid = [guid]::NewGuid().ToString()
    $wxs += "      <Component Id='cmp_$($guid.Replace("-", "_"))' Guid='{$guid}'>`n"
    $wxs += "        <File Id='fil_$($guid.Replace("-", "_"))' Source='$($file.FullName)' KeyPath='yes' />`n"
    $wxs += "      </Component>`n"
}

$wxs += @"
    </ComponentGroup>
  </Fragment>
</Wix>
"@

Set-Content -Path $WxsFile -Value $wxs -Encoding UTF8

# Build MSI
Write-Host "Building MSI..."
candle.exe $WxsFile
light.exe -ext WixUIExtension installer.wixobj -o $OutputMsi

Write-Host "MSI created: $OutputMsi"
