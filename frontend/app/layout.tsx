import type {Metadata} from 'next';
import './globals.css';
import {AppShell} from '../components/AppShell';
import {EngagementProvider} from '../lib/engagement-context';
import {AuthProvider} from '../lib/auth-context';
import {SignInGate} from '../components/SignInGate';

export const metadata: Metadata = {
  title: 'EliteInteliA Intelligence Factory',
  description: 'Enterprise Data & AI Delivery Platform — from Intake to Intelligence at Scale',
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <SignInGate>
            <EngagementProvider>
              <AppShell>{children}</AppShell>
            </EngagementProvider>
          </SignInGate>
        </AuthProvider>
      </body>
    </html>
  );
}
