'use client';

import React, { Suspense, useState } from 'react';
import TopNavbar from './TopNavbar';
import MobileNav from './MobileNav';
import LeagueSidebar from './LeagueSidebar';
import Footer from './Footer';
import BitcoinModal from './BitcoinModal';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [showBitcoinModal, setShowBitcoinModal] = useState(false);
  const [showMobileDonateModal, setShowMobileDonateModal] = useState(false);

  return (
    <>
      <TopNavbar onOpenBitcoinModal={() => setShowBitcoinModal(true)} />
      <MobileNav onOpenMobileDonate={() => setShowMobileDonateModal(true)} />

      <div className="main-layout">
        <Suspense fallback={<aside className="sidebar d-none d-lg-block" />}>
          <LeagueSidebar />
        </Suspense>
        <main className="main-content">{children}</main>
      </div>

      <Footer />

      <BitcoinModal
        show={showBitcoinModal}
        onHide={() => setShowBitcoinModal(false)}
        showMobileDonate={showMobileDonateModal}
        onHideMobileDonate={() => setShowMobileDonateModal(false)}
        onOpenBitcoinFromMobile={() => setShowBitcoinModal(true)}
      />
    </>
  );
}
