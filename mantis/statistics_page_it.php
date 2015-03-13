<?php
	require_once( 'core.php' );

	auth_ensure_user_authenticated();

	$stat_type = '';
	if ( $_POST [ 'do_stat' ] == 'full' ) $stat_type = '-s';
	$out_format = 'html';
	if ( $_POST [ 'download' ] == 'csv' ) $out_format = 'csv';
	$users = str_replace ( ' ', '', $_POST [ 'user' ] );
	if ( $_POST [ 'start_status' ] &&  $_POST [ 'end_status' ] ) $transition = $_POST [ 'start_status' ].','.$_POST [ 'end_status' ];

	# modificare qui il percorso dell'applicazione Python in funzione della propria installazione
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
		<input type="submit" value="Scarica in formato CSV"></input>
		</form>
<?php
	}
	else {
?>
		<form id="main" action="statistics_page.php" method="POST">
		<input id="stat-type" name="do_stat" type="hidden" value="full">

		<table>
			<tr class="row-1">
				<td class="category" style="width: 10%">Nome utente</td>
				<td><input name="user" type="text"></input></td>
				<td>
					Nome di un utente, oppure prefisso del nome, oppure lista di nomi separati da virgola.<br/>
					Nel caso siano selezionati pi&ugrave; utenti le statistiche saranno la somma delle statistiche degli utenti.
				</td>
			</tr>
			<tr class="row-2">
				<td class="category">Stato iniziale</td>
				<td>
					<select id="start-status" name="start_status">
						<!-- questo e' un esempio di elenco con stati personalizzati aggiunti in Mantis -->
						<option value="assigned" selected="selected">Assegnato</option>
						<option value="resolved">Risolto</option>
						<option value="verified">Verificato</option>
						<option value="validated">Validato</option>
						<option value="to_be_published">Da pubblicare</option>
					</select>
				</td>
				<td rowspan="2">
					<p>Questi campi rappresentano la "transizione" da controllare. In altre parole: per l'utente selezionato
					le statistiche riguardano i bug che l'utente ha fatto passare dallo stato iniziale allo stato finale
					indicati.</p>
					<p>La seguente tendina contiene alcuni valori predefiniti:</p>
					<p>
						<select id="transition-type" onchange="javascript:statistics_transition_set();">
							<option value="assigned,resolved" selected="selected">Fornitori (Assegnato -&gt; Risolto)</option>
							<option value="resolved,verified">Sviluppo EE (Risolto -&gt; Verificato)</option>
							<option value="verified,validated">PM EE (Verificato -&gt; Validato)</option>
							<option value="validated,to_be_published">Redazione (Validato -&gt; Da pubblicare)</option>
						</select>
					</p>
				</td>
			</tr>
			<tr class="row-1">
				<td class="category">Stato finale</td>
				<td>
					<select id="end-status" name="end_status">
						<option value="assigned">Assegnato</option>
						<option value="resolved" selected="selected">Risolto</option>
						<option value="verified">Verificato</option>
						<option value="validated">Validato</option>
						<option value="to_be_published">Da pubblicare</option>
					</select>
				</td>
			</tr>
			<tr class="row-2">
				<td colspan="2">
					<button onclick="javascript:statistics_report('expired');">Report bug scaduti per utente</button>
				</td>
				<td>
					Elenca i bug che l'utente selezionato non ha gestito nei tempi concordati e che, quindi, sono scaduti.
				</td>
			</tr>
			<tr class="row-1">
				<td colspan="2">
					<button onclick="javascript:statistics_report('full');">Statistiche per utente</button>
				</td>
				<td>
					Contiene il numero di bug che l'utente selezionato non ha gestito nei tempi concordati nel corso degli anni.
				</td>
			</tr>
			<tr class="row-2">
				<td colspan="3">
				<!-- I tempi dipendono dal valore del parametro "-d" passato nella stringa $command -->
				<p>I <b>tempi concordati</b> dipendono dalla priorit&agrave; del bug e sono cos&igrave; stabiliti:
				<ul>
					<li>Priorit&agrave; normale: 4 giorni di presa in carico + 4 giorni per la risoluzione;</li>
					<li>Priorit&agrave; alta: 2 giorni di presa in carico + 2 giorni per la risoluzione;</li>
					<li>Priorit&agrave; urgente: 1 giorno di presa in carico + 1 giorno per la risoluzione.</li>
				</ul>
				Attualmente non c'&egrave; modo di distinguere la presa in carico, quindi un bug viene considerato scaduto solo
				se supera la somma dei due tempi.</p>

				<p>Anche per gli interni sono considerati gli stessi tempi: vengono calcolati considerando il tempo
				intercorso nel passaggio dallo stato inziale allo stato finale indicati.</p>
				</td>
			</tr>
		</table>

		</form>
<?php
	}

	html_page_bottom ();
?>
