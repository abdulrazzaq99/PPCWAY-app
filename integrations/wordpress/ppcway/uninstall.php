<?php
/**
 * Removing the plugin removes its one setting. Nothing else was stored here:
 * the visits and leads live in PPCWay, under the merchant's own account.
 */
if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
	exit;
}
delete_option( 'ppcway' );
