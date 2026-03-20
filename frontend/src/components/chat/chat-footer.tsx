"use client";

import { useTranslation } from 'react-i18next';

export function ChatFooter() {
  const { t } = useTranslation('common');

  return (
    <footer className="py-2 text-center">
      <p className="text-[10px] text-[var(--text-tertiary)]">
        {t('poweredBy')}
      </p>
    </footer>
  );
}
