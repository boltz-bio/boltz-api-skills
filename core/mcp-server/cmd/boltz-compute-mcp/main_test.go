package main

import (
	"context"
	"os"
	"path/filepath"
	"runtime"
	"testing"
	"time"
)

func TestAuthDeviceCodeToolsWrapCLIJSONEvents(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("test uses a POSIX shell fake boltz-api")
	}

	resetPendingAuthLoginsForTest()
	installFakeBoltzAPI(t, `#!/bin/sh
if [ "$*" = "--no-browser auth login --device-code --json-events" ]; then
  echo '{"event":"auth_url","url":"https://auth.example/device?user_code=WDJB-MJHT","verification_uri":"https://auth.example/device","verification_uri_complete":"https://auth.example/device?user_code=WDJB-MJHT","user_code":"WDJB-MJHT","expires_in":600,"interval":5}'
  sleep 0.1
  echo '{"event":"success"}'
  exit 0
fi
if [ "$*" = "--format json auth status" ]; then
  echo '{"authenticated":false,"effective_mode":"none"}'
  exit 1
fi
if [ "$*" = "auth logout" ]; then
  echo 'Logged out.'
  exit 0
fi
echo "unexpected args: $*" >&2
exit 2
`)

	_, login, err := handleAuthLogin(context.Background(), nil, authLoginInput{})
	if err != nil {
		t.Fatalf("handleAuthLogin returned error: %v", err)
	}
	if login["status"] != "authorization_pending" {
		t.Fatalf("expected authorization_pending login status, got %#v", login["status"])
	}
	if login["user_code"] != "WDJB-MJHT" {
		t.Fatalf("expected user_code from JSON event, got %#v", login["user_code"])
	}
	pendingID, ok := login["pending_id"].(string)
	if !ok || pendingID == "" {
		t.Fatalf("expected pending_id string, got %#v", login["pending_id"])
	}

	var complete map[string]any
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		_, complete, err = handleAuthComplete(context.Background(), nil, authCompleteInput{PendingID: pendingID})
		if err != nil {
			t.Fatalf("handleAuthComplete returned error: %v", err)
		}
		if complete["status"] == "success" {
			break
		}
		time.Sleep(25 * time.Millisecond)
	}
	if complete["status"] != "success" {
		t.Fatalf("expected completed auth status, got %#v", complete)
	}

	_, status, err := handleAuthStatus(context.Background(), nil, noInput{})
	if err != nil {
		t.Fatalf("handleAuthStatus returned error: %v", err)
	}
	parsed, ok := status["status"].(map[string]any)
	if !ok {
		t.Fatalf("expected parsed status object, got %#v", status["status"])
	}
	if parsed["authenticated"] != false {
		t.Fatalf("expected unauthenticated status, got %#v", parsed["authenticated"])
	}
	if status["exit_error"] == "" {
		t.Fatalf("expected exit_error when CLI exits non-zero with structured status")
	}

	_, logout, err := handleAuthLogout(context.Background(), nil, noInput{})
	if err != nil {
		t.Fatalf("handleAuthLogout returned error: %v", err)
	}
	if logout["raw_output"] != "Logged out." {
		t.Fatalf("expected logout output, got %#v", logout["raw_output"])
	}
}

func resetPendingAuthLoginsForTest() {
	pendingAuthLogins.Lock()
	defer pendingAuthLogins.Unlock()
	pendingAuthLogins.items = map[string]*pendingAuthLogin{}
}

func installFakeBoltzAPI(t *testing.T, script string) {
	t.Helper()
	binDir := t.TempDir()
	binaryPath := filepath.Join(binDir, "boltz-api")
	if err := os.WriteFile(binaryPath, []byte(script), 0o755); err != nil {
		t.Fatalf("write fake boltz-api: %v", err)
	}
	t.Setenv("PATH", binDir+string(os.PathListSeparator)+os.Getenv("PATH"))
}
