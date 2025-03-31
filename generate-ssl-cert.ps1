# PowerShell script to generate self-signed SSL certificates for Windows
# Run this script as Administrator to create certificates for HTTPS

# Create directory for SSL certificates if it doesn't exist
$sslDir = ".\ssl"
if (-not (Test-Path -Path $sslDir)) {
    New-Item -ItemType Directory -Path $sslDir | Out-Null
    Write-Host "Created SSL directory: $sslDir"
}

# Configure certificate parameters
$certName = "EmotionDetectionServer"
$dnsNames = "localhost"
$ip = "127.0.0.1"
$validityDays = 365

# Generate self-signed certificate
try {
    Write-Host "Generating self-signed SSL certificate..."
    
    $cert = New-SelfSignedCertificate `
        -Subject "CN=$certName" `
        -DnsName $dnsNames `
        -IPAddress $ip `
        -KeyAlgorithm RSA `
        -KeyLength 2048 `
        -NotBefore (Get-Date) `
        -NotAfter (Get-Date).AddDays($validityDays) `
        -CertStoreLocation "Cert:\LocalMachine\My" `
        -KeyUsage DigitalSignature, KeyEncipherment `
        -FriendlyName $certName

    # Export certificate to PFX file with private key
    $pfxPassword = ConvertTo-SecureString -String "password" -Force -AsPlainText
    $pfxPath = "$sslDir\cert.pfx"
    Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $pfxPassword | Out-Null
    
    # Export certificate to PEM format
    $certPath = "$sslDir\cert.pem"
    $keyPath = "$sslDir\key.pem"
    
    # Use OpenSSL to convert PFX to PEM (requires OpenSSL to be installed)
    # Check if OpenSSL is available
    if (Get-Command "openssl.exe" -ErrorAction SilentlyContinue) {
        Write-Host "Using OpenSSL to convert certificate to PEM format..."
        
        # Extract certificate
        openssl.exe pkcs12 -in $pfxPath -clcerts -nokeys -out $certPath -passin pass:password
        
        # Extract private key
        openssl.exe pkcs12 -in $pfxPath -nocerts -out $keyPath -passin pass:password -passout pass:password
        
        # Remove passphrase from private key
        $tempKeyPath = "$sslDir\temp_key.pem"
        openssl.exe rsa -in $keyPath -out $tempKeyPath -passin pass:password
        Remove-Item $keyPath
        Rename-Item $tempKeyPath $keyPath
        
        Write-Host "SSL certificate generated successfully!"
        Write-Host "Certificate: $certPath"
        Write-Host "Private Key: $keyPath"
    } else {
        Write-Host "OpenSSL not found in PATH. Certificate was exported as PFX only: $pfxPath"
        Write-Host "Please install OpenSSL or manually convert the PFX to PEM format."
    }
    
    Write-Host ""
    Write-Host "Note: For production, replace these with real certificates from a trusted CA."
    Write-Host "This self-signed certificate is intended for development only."
} catch {
    Write-Host "Error generating certificate: $_" -ForegroundColor Red
    
    # Provide alternative instructions if certificate generation fails
    Write-Host ""
    Write-Host "Alternative method:" -ForegroundColor Yellow
    Write-Host "If you have OpenSSL installed, you can generate certificates with these commands:" -ForegroundColor Yellow
    Write-Host "openssl req -x509 -newkey rsa:4096 -nodes -keyout .\ssl\key.pem -out .\ssl\cert.pem -days 365 -subj '/CN=localhost'" -ForegroundColor Yellow
}