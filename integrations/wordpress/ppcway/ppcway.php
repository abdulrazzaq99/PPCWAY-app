<?php
/**
 * Plugin Name:       PPCWay
 * Plugin URI:        https://ppcway.com
 * Description:       Counts your website's visits and leads (forms sent, phone numbers tapped) for PPCWay, so you can see which ads bring customers and send your jobs back to Google Ads.
 * Version:           1.0.0
 * Requires at least: 5.8
 * Requires PHP:      7.4
 * Author:            PPCWay
 * License:           GPL-2.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       ppcway
 *
 * What it does: adds the one-line PPCWay script to every page of the site,
 * with the key from your PPCWay account. The script reports page views and
 * leads to PPCWay; it never reads passwords or payment details, and it loads
 * after the page so it does not slow it down.
 *
 * What it does not do: hold any Google Ads access. PPCWay talks to Google
 * Ads; this plugin only tells PPCWay what happened on your site.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'PPCWAY_VERSION', '1.0.0' );
define( 'PPCWAY_SCRIPT', 'https://app.ppcway.com/t.js' );

/**
 * The key from the Website screen in PPCWay: "pw_" and letters, nothing else.
 */
function ppcway_clean_key( $value ) {
	$value = trim( (string) $value );
	return preg_match( '/^pw_[A-Za-z0-9_-]{10,40}$/', $value ) ? $value : '';
}

function ppcway_options() {
	$saved = get_option( 'ppcway', array() );
	return wp_parse_args(
		is_array( $saved ) ? $saved : array(),
		array(
			'key'          => '',
			'skip_signed'  => 1,
			'wait_consent' => 0,
		)
	);
}

/**
 * The script, in the head of every page, for visitors only.
 */
function ppcway_print_script() {
	if ( is_admin() || wp_doing_ajax() || ( function_exists( 'wp_is_json_request' ) && wp_is_json_request() ) ) {
		return;
	}
	$options = ppcway_options();
	$key     = ppcway_clean_key( $options['key'] );
	if ( '' === $key ) {
		return;
	}
	// Your own visits, and your staff's, would count as customers otherwise.
	if ( $options['skip_signed'] && is_user_logged_in() && current_user_can( 'edit_posts' ) ) {
		return;
	}
	$consent = $options['wait_consent'] ? ' data-consent="wait"' : '';
	printf(
		"<script async src=\"%s\" data-key=\"%s\"%s></script>\n",
		esc_url( PPCWAY_SCRIPT ),
		esc_attr( $key ),
		$consent // A fixed string or nothing, built above.
	);
	if ( $options['wait_consent'] ) {
		// Consent given before the script arrived is remembered and replayed.
		echo "<script>window.ppcway=window.ppcway||function(){(window.ppcway.q=window.ppcway.q||[]).push(arguments)};</script>\n";
	}
}
add_action( 'wp_head', 'ppcway_print_script', 1 );

/* --- Settings, PPCWay ---------------------------------------------------- */

function ppcway_settings_init() {
	register_setting(
		'ppcway',
		'ppcway',
		array(
			'type'              => 'array',
			'sanitize_callback' => 'ppcway_sanitize',
			'default'           => array(),
		)
	);
}
add_action( 'admin_init', 'ppcway_settings_init' );

function ppcway_sanitize( $input ) {
	$input = is_array( $input ) ? $input : array();
	$key   = ppcway_clean_key( isset( $input['key'] ) ? $input['key'] : '' );
	if ( '' === $key && ! empty( $input['key'] ) ) {
		add_settings_error( 'ppcway', 'ppcway_key', __( 'That does not look like a PPCWay key. Copy it from the Website screen in PPCWay; it starts with pw_.', 'ppcway' ) );
	}
	return array(
		'key'          => $key,
		'skip_signed'  => empty( $input['skip_signed'] ) ? 0 : 1,
		'wait_consent' => empty( $input['wait_consent'] ) ? 0 : 1,
	);
}

function ppcway_menu() {
	add_options_page( 'PPCWay', 'PPCWay', 'manage_options', 'ppcway', 'ppcway_settings_page' );
}
add_action( 'admin_menu', 'ppcway_menu' );

function ppcway_settings_page() {
	if ( ! current_user_can( 'manage_options' ) ) {
		return;
	}
	$options = ppcway_options();
	$key     = ppcway_clean_key( $options['key'] );
	?>
	<div class="wrap">
		<h1>PPCWay</h1>
		<p style="max-width:640px">
			<?php esc_html_e( 'PPCWay counts your website\'s visits and leads, so you can see which ads bring customers and send the jobs they became back to Google Ads.', 'ppcway' ); ?>
		</p>
		<?php if ( $key ) : ?>
			<div class="notice notice-success inline"><p>
				<?php esc_html_e( 'PPCWay is on your website. Open any page of your site, then look at the Website screen in PPCWay: it says Working within a minute.', 'ppcway' ); ?>
			</p></div>
		<?php endif; ?>
		<form action="options.php" method="post">
			<?php settings_fields( 'ppcway' ); ?>
			<table class="form-table" role="presentation">
				<tr>
					<th scope="row"><label for="ppcway-key"><?php esc_html_e( 'Your PPCWay key', 'ppcway' ); ?></label></th>
					<td>
						<input name="ppcway[key]" id="ppcway-key" type="text" class="regular-text code" value="<?php echo esc_attr( $options['key'] ); ?>" placeholder="pw_..." autocomplete="off" spellcheck="false" />
						<p class="description"><?php esc_html_e( 'In PPCWay, open Website and copy the key under WordPress.', 'ppcway' ); ?></p>
					</td>
				</tr>
				<tr>
					<th scope="row"><?php esc_html_e( 'Your own visits', 'ppcway' ); ?></th>
					<td>
						<label><input name="ppcway[skip_signed]" type="checkbox" value="1" <?php checked( $options['skip_signed'], 1 ); ?> />
						<?php esc_html_e( 'Do not count visits from people signed in to this WordPress who can edit it', 'ppcway' ); ?></label>
					</td>
				</tr>
				<tr>
					<th scope="row"><?php esc_html_e( 'Cookie consent', 'ppcway' ); ?></th>
					<td>
						<label><input name="ppcway[wait_consent]" type="checkbox" value="1" <?php checked( $options['wait_consent'], 1 ); ?> />
						<?php esc_html_e( 'Wait until the visitor agrees', 'ppcway' ); ?></label>
						<p class="description"><?php echo wp_kses( __( 'Your consent banner then needs to run <code>ppcway("consent")</code> when the visitor agrees to statistics.', 'ppcway' ), array( 'code' => array() ) ); ?></p>
					</td>
				</tr>
			</table>
			<?php submit_button(); ?>
		</form>
	</div>
	<?php
}

function ppcway_action_links( $links ) {
	$url = admin_url( 'options-general.php?page=ppcway' );
	array_unshift( $links, '<a href="' . esc_url( $url ) . '">' . esc_html__( 'Settings', 'ppcway' ) . '</a>' );
	return $links;
}
add_filter( 'plugin_action_links_' . plugin_basename( __FILE__ ), 'ppcway_action_links' );
