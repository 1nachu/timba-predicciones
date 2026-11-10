'use client';

import React, { useState } from 'react';
import { Modal, Button } from 'react-bootstrap';

export const BTC_ADDRESS = 'bc1phgvsg3mgrvp3jtukj7uh8aadsm8xa520u4gdk3lrdjkk5pzxnjest3439j';

interface BitcoinModalProps {
  show: boolean;
  onHide: () => void;
  showMobileDonate?: boolean;
  onHideMobileDonate?: () => void;
  onOpenBitcoinFromMobile?: () => void;
}

export default function BitcoinModal({
  show,
  onHide,
  showMobileDonate = false,
  onHideMobileDonate,
  onOpenBitcoinFromMobile,
}: BitcoinModalProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(BTC_ADDRESS);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore clipboard errors
    }
  };

  return (
    <>
      <Modal
        show={show}
        onHide={onHide}
        centered
        id="bitcoinModal"
        aria-labelledby="bitcoinModalLabel"
      >
        <Modal.Header closeButton closeVariant="white">
          <Modal.Title
            id="bitcoinModalLabel"
            className="d-flex align-items-center gap-2 fs-5"
          >
            <i className="bi bi-coin text-warning"></i> Donar con Bitcoin (BTC)
          </Modal.Title>
        </Modal.Header>
        <Modal.Body className="text-center p-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/btc_qr.png"
            alt="QR Bitcoin"
            width={180}
            className="img-fluid rounded border border-secondary p-2 mb-3 bg-white"
          />
          <div className="d-flex align-items-center justify-content-center gap-2 flex-wrap">
            <code
              id="btcAddress"
              className="p-2 rounded bg-dark border border-secondary text-info text-break"
              style={{ fontSize: '11.5px', flex: 1 }}
            >
              {BTC_ADDRESS}
            </code>
            <button
              type="button"
              className={`btn btn-copy ${copied ? 'copied' : ''}`}
              id="copyBtcBtn"
              title="Copiar dirección"
              onClick={handleCopy}
            >
              {copied ? (
                <>
                  <i className="bi bi-check2-all"></i> ¡Copiado!
                </>
              ) : (
                <>
                  <i className="bi bi-clipboard-data"></i> Copiar
                </>
              )}
            </button>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" size="sm" onClick={onHide}>
            Cerrar
          </Button>
        </Modal.Footer>
      </Modal>

      {onHideMobileDonate && (
        <Modal
          show={showMobileDonate}
          onHide={onHideMobileDonate}
          centered
          id="mobiledonateModal"
          aria-labelledby="mobiledonateModalLabel"
        >
          <Modal.Header closeButton closeVariant="white">
            <Modal.Title id="mobiledonateModalLabel" className="fs-5">
              Apoyar el Proyecto
            </Modal.Title>
          </Modal.Header>
          <Modal.Body className="p-3">
            <div className="d-grid gap-2">
              <a
                href="https://cafecito.app/timba_arg"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-outline-success"
              >
                🇦🇷 Cafecito App
              </a>
              <a
                href="https://buymeacoffee.com/timba_global"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-outline-success"
              >
                🌍 Buy Me a Coffee
              </a>
              <button
                type="button"
                className="btn btn-outline-warning"
                onClick={() => {
                  onHideMobileDonate();
                  onOpenBitcoinFromMobile?.();
                }}
              >
                ₿ Bitcoin / Crypto
              </button>
            </div>
          </Modal.Body>
        </Modal>
      )}
    </>
  );
}
