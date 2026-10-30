<?php

/**
 * SPDX-FileCopyrightText: 2026 Nikita <it@aniops.by>
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

declare(strict_types=1);

namespace OCA\DeckCardNumber\Listener;

use OCA\Deck\Db\CardMapper;
use OCA\Deck\Event\CardCreatedEvent;
use OCP\EventDispatcher\Event;
use OCP\EventDispatcher\IEventListener;
use Psr\Log\LoggerInterface;

/**
 * Prefixes the title of every freshly created Deck card with "#<card id>".
 *
 * The card id only exists after the INSERT, so this runs on CardCreatedEvent,
 * which Deck dispatches from CardService::create() with the very entity it
 * returns to the client. Mutating that entity means the API/UI response already
 * carries the numbered title, with no second request and no window where the
 * card exists without a number.
 *
 * @template-implements IEventListener<Event>
 */
class CardCreatedListener implements IEventListener {
	public function __construct(
		private CardMapper $cardMapper,
		private LoggerInterface $logger,
	) {
	}

	public function handle(Event $event): void {
		if (!($event instanceof CardCreatedEvent)) {
			return;
		}

		$card = $event->getCard();
		$id = (int)($card->getId() ?? 0);
		$title = trim((string)$card->getTitle());
		if ($id <= 0 || $title === '') {
			return;
		}

		if (preg_match('/^#' . $id . '(?:\s|$)/u', $title) === 1) {
			return; // already numbered with its own id
		}

		// a copied card keeps the source card's number - replace it, do not stack
		$stripped = preg_replace('/^#\d+\s+/u', '', $title) ?? $title;
		$card->setTitle('#' . $id . ' ' . $stripped);

		try {
			$this->cardMapper->update($card);
		} catch (\Throwable $e) {
			$this->logger->warning('deckcardnumber: cannot rename card ' . $id . ': ' . $e->getMessage(), ['app' => 'deckcardnumber']);
		}
	}
}
