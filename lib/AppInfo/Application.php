<?php

/**
 * SPDX-FileCopyrightText: 2026 Nikita <it@aniops.by>
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

declare(strict_types=1);

namespace OCA\DeckCardNumber\AppInfo;

use OCA\Deck\Event\CardCreatedEvent;
use OCA\DeckCardNumber\Listener\CardCreatedListener;
use OCP\AppFramework\App;
use OCP\AppFramework\Bootstrap\IBootContext;
use OCP\AppFramework\Bootstrap\IBootstrap;
use OCP\AppFramework\Bootstrap\IRegistrationContext;

class Application extends App implements IBootstrap {
	public const APP_ID = 'deckcardnumber';

	public function __construct() {
		parent::__construct(self::APP_ID);
	}

	public function register(IRegistrationContext $context): void {
		$context->registerEventListener(CardCreatedEvent::class, CardCreatedListener::class);
	}

	public function boot(IBootContext $context): void {
	}
}
