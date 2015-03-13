<?php
	require_once( 'core.php' );

	auth_ensure_user_authenticated();

	$stat_type = '';
	if ( $_POST [ 'do_stat' ] == 'full' ) $stat_type = '-s';
	$out_format = 'html';
	if ( $_POST [ 'download' ] == 'csv' ) $out_format = 'csv';
	$users = str_replace ( ' ', '', $_POST [ 'user' ] );
	if ( $_POST [ 'start_status' ] &&  $_POST [ 'end_status' ] ) $transition = $_POST [ 'start_status' ].','.$_POST [ 'end_status' ];

	# change the executable path and the parameters depending on your setup
	$command = '../bin/mantis_statistics.py -u '.$users.' '.$stat_type.' -f '.$out_format.' -t '.$transition.' -l "dummy"';

	if ( $_POST [ 'do_stat' ] and $_POST [ 'download' ] ) {
		header("Content-disposition: attachment; filename=statistics.csv");
		header("Content-Type: text/csv");

		system ( $command );
		return;
	}

	html_page_top ( lang_get ( 'statistics_menu' ) );
?>

	<script type="text/javascript" language="JavaScript">
		function statistics_report ( stype ) {
			var do_stat = document.getElementById ( "stat-type" );
			var form = document.getElementById ( "main" );
			do_stat.value = stype;
			form.submit ();
		}

		function statistics_transition_set () {
			var tlist = document.getElementById ( "transition-type" );
			var start = document.getElementById ( "start-status" );
			var end = document.getElementById ( "end-status" );

			var ttype = tlist.options [ tlist.selectedIndex ].value;
			var p = ttype.split ( ',' );

			var i = 0;
			for ( i = 0; i < start.options.length; i++ )
				if ( start.options [ i ].value == p [ 0 ] ) {
					start.selectedIndex = i;
					break;
				}

			for ( i = 0; i < end.options.length; i++ )
				if ( end.options [ i ].value == p [ 1 ] ) {
					end.selectedIndex = i;
					break;
				}
		}
	</script>

	<div style="margin-top: 5px;">&nbsp;</div>

<?php
	if ( $_POST [ 'do_stat' ] ) {
		system ( $command );
?>
		<div style="margin-top: 5px;">&nbsp;</div>
		<form action="statistics_page.php" method="POST">
		<input name="do_stat" type="hidden" value="<?php echo $_POST [ 'do_stat' ] ?>">
		<input name="download" type="hidden" value="csv">
		<input name="user" type="hidden" value="<?php echo $users ?>">
		<input name="start_status" type="hidden" value="<?php echo $_POST [ 'start_status' ] ?>">
		<input name="end_status" type="hidden" value="<?php echo $_POST [ 'end_status' ] ?>">
		<input type="submit" value="Donwload CSV format"></input>
		</form>
<?php
	}
	else {
?>
		<form id="main" action="statistics_page.php" method="POST">
		<input id="stat-type" name="do_stat" type="hidden" value="full">

		<table>
			<tr class="row-1">
				<td class="category" style="width: 10%">User name</td>
				<td><input name="user" type="text"></input></td>
				<td>
					User name, or name prefix, or comma separated name list.<br/>
					If there's more than one user name the resulting statistics will be the sum of the statistics of each user.
				</td>
			</tr>
			<tr class="row-2">
				<td class="category">Start status</td>
				<td>
					<select id="start-status" name="start_status">
						<!-- change here if you have custom status -->
						<option value="assigned" selected="selected">Assigned</option>
						<option value="resolved">Resolved</option>
						<option value="closed">Closed</option>
					</select>
				</td>
				<td rowspan="2">
					<p>These fields define the "transition" to be checked. That is: for the chosen user the statistics are
					about the bugs that the user has transitioned from the start status to the end status.</p>
					<p>The following selection contains some predefined "transitions":</p>
					<p>
						<select id="transition-type" onchange="javascript:statistics_transition_set();">
							<option value="assigned,resolved" selected="selected">External providers (Assigned -&gt; Resolved)</option>
							<option value="resolved,closed">Internals (Resolved -&gt; Closed)</option>
							<!-- others go here -->
						</select>
					</p>
				</td>
			</tr>
			<tr class="row-1">
				<td class="category">End status</td>
				<td>
					<select id="end-status" name="end_status">
						<!-- change here if you have custom status -->
						<option value="assigned">Assigned</option>
						<option value="resolved" selected="selected">Resolved</option>
						<option value="closed">Closed</option>
					</select>
				</td>
			</tr>
			<tr class="row-2">
				<td colspan="2">
					<button onclick="javascript:statistics_report('expired');">Report expired bugs for user</button>
				</td>
				<td>
					Lists the bugs that the chosen user has not handled in due time.
				</td>
			</tr>
			<tr class="row-1">
				<td colspan="2">
					<button onclick="javascript:statistics_report('full');">Statistics for user</button>
				</td>
				<td>
					Contains the number of bugs that the chosen user has not handled in due time during the years.
				</td>
			</tr>
			<tr class="row-2">
				<td colspan="3">
				<!-- change depending on the parameter "-d" you use in the $command string -->
				<p><b>Due times</b> are dependent on the bug priority and are the following:
				<ul>
					<li>normal priority: 8 days;</li>
					<li>high priority: 4 days;</li>
					<li>urgent priority: 2 days.</li>
				</ul>
				</p>
				</td>
			</tr>
		</table>

		</form>
<?php
	}

	html_page_bottom ();
?>
